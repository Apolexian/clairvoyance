"""
Uma Musume API client for the crawler.
No Frida required — pure HTTP with AES-CBC packet encryption.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import platform
import random
import shutil
import socket
import struct
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import msgpack
try:
    from curl_cffi import requests  # TLS fingerprint must match the game client
except ImportError:
    import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

log = logging.getLogger("crawler.client")

_TICKET_GEN_JS = r"""
const SteamUser = require("steam-user");
const args = process.argv.slice(2);
let username = "", password = "", appid = 3224770, code = "";
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--username") username = args[++i];
  else if (args[i] === "--password") password = args[++i];
  else if (args[i] === "--appid") appid = parseInt(args[++i]);
  else if (args[i] === "--code") code = args[++i];
}
if (!username || !password) { process.stderr.write("missing credentials\n"); process.exit(1); }
const client = new SteamUser();
const loginOpts = { accountName: username, password: password };
if (code) loginOpts.twoFactorCode = code;
client.logOn(loginOpts);
client.on("steamGuard", (domain, callback) => { process.stderr.write("NEED_GUARD:" + (domain || "2fa") + "\n"); process.exit(2); });
client.on("error", (err) => { process.stderr.write("ERROR:" + err.message + "\n"); process.exit(1); });
client.on("loggedOn", () => {
  client.createAuthSessionTicket(appid, (err, sessionTicket) => {
    if (err) { process.stderr.write("Ticket error: " + err.message + "\n"); process.exit(1); }
    const buf = Buffer.isBuffer(sessionTicket) ? sessionTicket : sessionTicket.sessionTicket || sessionTicket;
    process.stdout.write(JSON.stringify({ steam_id: client.steamID.getSteamID64(), session_ticket: Buffer.from(buf).toString("hex").toUpperCase() }) + "\n");
    setTimeout(() => process.exit(0), 500);
  });
});
"""

_TICKET_JS_PATH = Path(__file__).parent / "_ticket_gen.js"
_NODE_MODULES_DIR = Path(__file__).parent


def _ensure_ticket_deps() -> None:
    if not shutil.which("node"):
        raise RuntimeError("node not found — install Node.js to refresh Steam tickets")
    pkg = _NODE_MODULES_DIR / "node_modules" / "steam-user"
    if not pkg.exists():
        log.info("Installing steam-user npm package...")
        subprocess.run(
            ["npm", "install", "steam-user", "--silent"],
            check=True,
            cwd=str(_NODE_MODULES_DIR),
        )


def get_steam_ticket(username: str, password: str, code: str = "") -> tuple[str, str]:
    """Return (steam_id, session_ticket_hex). Raises on failure."""
    _ensure_ticket_deps()
    if not _TICKET_JS_PATH.exists():
        _TICKET_JS_PATH.write_text(_TICKET_GEN_JS, encoding="utf-8")
    cmd = ["node", str(_TICKET_JS_PATH), "--username", username, "--password", password]
    if code:
        cmd += ["--code", code]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode == 2:
        raise RuntimeError("STEAM_GUARD_REQUIRED")
    out = proc.stdout.strip()
    if not out or proc.returncode != 0:
        raise RuntimeError(f"Steam ticket failed: {proc.stderr.strip() or 'unknown error'}")
    try:
        d = json.loads(out.split("\n")[-1])
        return d["steam_id"], d["session_ticket"]
    except Exception as exc:
        raise RuntimeError(f"Bad ticket JSON: {out[:200]}") from exc


_FRIDA_SNIFF_JS = r"""
(function() {
    var _seq = 0;
    var mods = ["ssl", "libssl", "boringssl", "libcrypto"];
    Process.enumerateModules().forEach(function(m) {
        var name = m.name.toLowerCase();
        if (!mods.some(function(k){ return name.indexOf(k) >= 0; })) return;
        var readFn = m.findExportByName("SSL_read");
        if (!readFn) return;
        Interceptor.attach(readFn, {
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n <= 0) return;
                try {
                    var buf = this.context.rsi || this.context.r1 || this.context.x1;
                    if (!buf || buf.isNull()) return;
                    var text = buf.readUtf8String(Math.min(n, 2048));
                    if (!text) return;
                    var appM = text.match(/APP-VER:\s*([^\r\n]+)/i);
                    var resM = text.match(/RES-VER:\s*([^\r\n]+)/i);
                    if (appM && resM) {
                        send({type:"versions", app_ver: appM[1].trim(), res_ver: resM[1].trim()});
                    }
                } catch(e) {}
            }
        });
    });
    // Also hook via schannel on Windows
    try {
        var secur32 = Process.getModuleByName("secur32.dll") || Process.getModuleByName("ncrypt.dll");
        if (secur32) {
            var decryptMsg = secur32.findExportByName("DecryptMessage");
            if (decryptMsg) {
                Interceptor.attach(decryptMsg, {
                    onLeave: function(retval) {
                        try {
                            var buf = this.context.rdx;
                            if (!buf || buf.isNull()) return;
                            var cbuf = buf.add(Process.pointerSize * 2).readPointer();
                            var len = buf.add(Process.pointerSize * 2 + Process.pointerSize).readU32();
                            if (!cbuf || cbuf.isNull() || len < 10 || len > 32768) return;
                            var text = cbuf.readUtf8String(Math.min(len, 2048));
                            if (!text) return;
                            var appM = text.match(/APP-VER:\s*([^\r\n]+)/i);
                            var resM = text.match(/RES-VER:\s*([^\r\n]+)/i);
                            if (appM && resM) {
                                send({type:"versions", app_ver: appM[1].trim(), res_ver: resM[1].trim()});
                            }
                        } catch(e) {}
                    }
                });
            }
        }
    } catch(e) {}
})();
"""


def detect_versions(timeout: int = 30) -> tuple[str, str]:
    """
    Attach to the running game via Frida and sniff APP-VER / RES-VER
    from the first outbound HTTPS request.
    Returns ("", "") if game is not running or Frida unavailable.
    """
    try:
        import frida
    except ImportError:
        return "", ""

    result: dict = {}

    def on_message(msg: dict, _data: object) -> None:
        if msg.get("type") == "send":
            payload = msg.get("payload") or {}
            if payload.get("type") == "versions":
                result["app_ver"] = payload["app_ver"]
                result["res_ver"] = payload["res_ver"]

    process_names = ["UmamusumePrettyDerby.exe", "UmamusumePrettyDerby"]
    session = None
    for name in process_names:
        try:
            session = frida.attach(name)
            break
        except Exception:
            pass

    if session is None:
        return "", ""

    try:
        script = session.create_script(_FRIDA_SNIFF_JS, runtime="v8")
        script.on("message", on_message)
        script.load()
        log.info("Attached to game — waiting up to %ds for a network request...", timeout)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and "app_ver" not in result:
            time.sleep(0.2)
        script.unload()
        session.detach()
    except Exception as exc:
        log.debug("Version sniff failed: %s", exc)
        try:
            session.detach()
        except Exception:
            pass

    if "app_ver" in result:
        log.info("Detected: APP-VER=%s RES-VER=%s", result["app_ver"], result["res_ver"])
        return result["app_ver"], result["res_ver"]
    return "", ""

BASE_URL = "https://api.games.umamusume.com/umamusume/"

SALT = b"co!=Y;(UQCGxJ_n82"

# Fixed blob1 header prefix (constant across all clients)
HEAD = bytes.fromhex(
    "6b20e2ab6c311330f761d737ce3f3025750850665eea58b6372f8d2f57501eb3"
    "44bdb7270a9067f5b63cd61f152cfb986cbfbf7a"
)

# Default version strings — update when game updates.
# These are used only as a last-resort fallback; detect_versions() tries
# to read them from the most recent clairvoyance session first.
DEFAULT_UNITY_VER = "2022.3.62f2"
DEFAULT_APP_VER = ""   # must be filled in — see detect_versions()
DEFAULT_RES_VER = ""   # must be filled in — see detect_versions()


# ── Crypto helpers ────────────────────────────────────────────────────────────

def _sm5(data: bytes) -> bytes:
    h = hashlib.md5()
    h.update(data)
    h.update(SALT)
    return h.digest()


def _make_sid(viewer_id: int, udid: str) -> bytes:
    return _sm5((str(viewer_id) + udid).encode())


def _next_sid(sid: bytes) -> bytes:
    return _sm5(sid.hex().encode())


def _gen_key() -> bytes:
    out = b""
    while len(out) < 32:
        out += format(random.randint(0, 65535), "x").encode()
    return out[:32]


def _get_iv(udid: str) -> bytes:
    return udid.replace("-", "").lower()[:16].encode()


def _get_raw_udid(udid: str) -> bytes:
    return bytes.fromhex(udid.replace("-", "").lower())


def _pack(sid: bytes, udid: str, auth: bytes | None, payload: dict) -> bytes:
    key = _gen_key()
    p = msgpack.packb(payload, use_bin_type=True)
    body = (
        AES.new(key, AES.MODE_CBC, _get_iv(udid)).encrypt(
            pad(struct.pack("<I", len(p)) + p, 16)
        )
        + key
    )
    h = HEAD + sid + _get_raw_udid(udid) + os.urandom(32)
    h += auth if auth else bytes(48)  # server expects 164-byte blob1; zeros for new accounts
    return base64.b64encode(struct.pack("<I", len(h)) + h + body)


def _unpack(text: str, udid: str) -> dict:
    raw = base64.b64decode(text.strip())
    key = raw[-32:]
    cipher = raw[:-32]
    p = unpad(AES.new(key, AES.MODE_CBC, _get_iv(udid)).decrypt(cipher), 16)
    size = struct.unpack("<I", p[:4])[0]
    return msgpack.unpackb(p[4 : 4 + size], raw=False, strict_map_key=False)


# ── Hardware profile ──────────────────────────────────────────────────────────

def _get_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_gpu() -> str:
    if platform.system() != "Windows":
        return "NVIDIA GeForce RTX 3070"
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Video",
        ) as video_key:
            for i in range(winreg.QueryInfoKey(video_key)[0]):
                adapter_guid = winreg.EnumKey(video_key, i)
                adapter_path = (
                    rf"SYSTEM\CurrentControlSet\Control\Video\{adapter_guid}\0000"
                )
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, adapter_path
                    ) as ak:
                        value, _ = winreg.QueryValueEx(
                            ak, "HardwareInformation.AdapterString"
                        )
                        if isinstance(value, bytes):
                            value = value.decode("utf-16-le", errors="ignore")
                        gpu = str(value).replace("\x00", "").strip()
                        if gpu:
                            return gpu
                except OSError:
                    continue
    except Exception:
        pass
    return "NVIDIA GeForce RTX 3070"


def build_profile(seed: str = "crawler") -> dict:
    """Generate a stable hardware profile from a seed string."""
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\BIOS"
            ) as bios_key:
                device_name, _ = winreg.QueryValueEx(bios_key, "SystemProductName")
                device_name = str(device_name).strip()
            machine_guid = ""
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                ) as ck:
                    machine_guid, _ = winreg.QueryValueEx(ck, "MachineGuid")
            except OSError:
                pass
            hardware_string = f"{device_name}_{machine_guid}_{seed}"
            device_id = hashlib.sha1(hardware_string.encode()).hexdigest()
        except Exception:
            device_name = "Generic PC"
            device_id = hashlib.sha1(seed.encode()).hexdigest()
    else:
        device_name = "Generic PC"
        device_id = hashlib.sha1(seed.encode()).hexdigest()

    return {
        "device_name": device_name,
        "graphics_device_name": _get_gpu(),
        "platform_os_version": f"Windows 11  ({platform.version()}) 64bit",
        "ip_address": _get_ip(),
        "udid": str(uuid.uuid4()).lower(),
        "device_id": device_id,
    }


# ── API Client ────────────────────────────────────────────────────────────────

class UmaClient:
    def __init__(self, cfg: dict) -> None:
        self.viewer_id: int = cfg.get("viewer_id", 0)
        self.udid: str = cfg.get("udid") or str(uuid.uuid4()).lower()
        self.auth_key_hex: str = cfg.get("auth_key", "")
        self.steam_id: str = str(cfg.get("steam_id", ""))
        self.steam_ticket: str = cfg.get("steam_session_ticket", "")
        self.steam_username: str = cfg.get("steam_username", "")
        self.steam_password: str = cfg.get("steam_password", "")

        profile = cfg.get("_profile") or build_profile()
        self.device_id: str = cfg.get("device_id") or profile["device_id"]
        self.device_name: str = cfg.get("device_name") or profile["device_name"]
        self.graphics_device: str = (
            cfg.get("graphics_device_name") or profile["graphics_device_name"]
        )
        self.ip_address: str = cfg.get("ip_address") or profile["ip_address"]
        self.platform_os: str = (
            cfg.get("platform_os_version") or profile["platform_os_version"]
        )
        self.locale: str = cfg.get("locale", "JPN")
        self.unity_ver: str = cfg.get("unity_ver", DEFAULT_UNITY_VER)
        self.app_ver: str = cfg.get("app_ver") or DEFAULT_APP_VER
        self.res_ver: str = cfg.get("res_ver") or DEFAULT_RES_VER
        if not self.app_ver or not self.res_ver:
            # Try versions.json — check repo root and /data (Docker volume)
            for versions_file in [
                Path(__file__).parent.parent / "versions.json",
                Path("/data/versions.json"),
            ]:
                if versions_file.exists():
                    try:
                        v = json.loads(versions_file.read_text(encoding="utf-8"))
                        self.app_ver = self.app_ver or v.get("app_ver", "")
                        self.res_ver = self.res_ver or v.get("res_ver", "")
                    except Exception:
                        pass
        if not self.app_ver or not self.res_ver:
            detected_app, detected_res = detect_versions()
            self.app_ver = self.app_ver or detected_app
            self.res_ver = self.res_ver or detected_res
        if not self.app_ver or not self.res_ver:
            raise RuntimeError(
                "APP-VER / RES-VER unknown. "
                "Run: python get_versions.py  (with the game open), then retry."
            )

        self.sid: bytes = bytes(16)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": f"UnityPlayer/{self.unity_ver} (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
                "Accept": "*/*",
                "Accept-Encoding": "deflate, gzip",
                "Content-Type": "application/x-msgpack",
                "X-Unity-Version": self.unity_ver,
            }
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    @property
    def _auth_bytes(self) -> bytes | None:
        if self.auth_key_hex and self.auth_key_hex != "YOUR_AUTH_KEY_HERE":
            try:
                return bytes.fromhex(self.auth_key_hex)
            except ValueError:
                pass
        return None

    def _regen_sid(self) -> None:
        if self.viewer_id:
            self.sid = _make_sid(self.viewer_id, self.udid)
        else:
            self.sid = bytes(16)

    def _common(self) -> dict:
        return {
            "viewer_id": self.viewer_id,
            "device": 4,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "graphics_device_name": self.graphics_device,
            "ip_address": self.ip_address,
            "platform_os_version": self.platform_os,
            "carrier": "",
            "keychain": 0,
            "locale": self.locale,
            "button_info": "",
            "dmm_viewer_id": None,
            "dmm_onetime_token": None,
            "steam_id": self.steam_id,
            "steam_session_ticket": self.steam_ticket,
        }

    # ── Core call ─────────────────────────────────────────────────────────

    def call(
        self,
        ep: str,
        args: dict | None = None,
        retry_208: int = 4,
        retry_205: int = 2,
    ) -> dict:
        payload: dict[str, Any] = dict(args or {})
        payload.update(self._common())

        body = _pack(self.sid, self.udid, self._auth_bytes, payload)
        headers = {
            "SID": self.sid.hex(),
            "Device": "4",
            "ViewerID": str(self.viewer_id),
            "APP-VER": self.app_ver,
            "RES-VER": self.res_ver,
        }

        for attempt in range(6):
            try:
                resp = self.session.post(
                    BASE_URL + ep, data=body, headers=headers, timeout=30
                )
                break
            except Exception as exc:
                if attempt < 5:
                    time.sleep(min(2.0 + attempt * 2, 12))
                    continue
                raise RuntimeError(f"Network error on {ep}: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code} on {ep}: {resp.text[:300]}")

        res = _unpack(resp.text, self.udid)
        dh = res.get("data_headers", {})
        rc = dh.get("result_code", 0)

        # Update viewer_id if server corrects it
        server_vid = dh.get("viewer_id")
        if server_vid and server_vid != self.viewer_id:
            self.viewer_id = server_vid
            self._regen_sid()

        if rc == 205 and retry_205 > 0:
            time.sleep(0.2)
            return self.call(ep, args, retry_208=retry_208, retry_205=retry_205 - 1)
        if rc == 208 and retry_208 > 0:
            time.sleep(1.0)
            return self.call(ep, args, retry_208=retry_208 - 1)
        if rc not in (0, 1):
            raise RuntimeError(f"API error {rc} on {ep} — response: {json.dumps(res, ensure_ascii=False, default=str)[:500]}")

        # Use server-returned SID if present, otherwise advance locally
        # Server appends a 10-digit unix timestamp to the 32-char hex SID
        server_sid = dh.get("sid")
        if server_sid and isinstance(server_sid, str) and len(server_sid) >= 32:
            try:
                self.sid = bytes.fromhex(server_sid[:32])
            except ValueError:
                self.sid = _next_sid(self.sid)
        else:
            self.sid = _next_sid(self.sid)
        return res

    # ── Auth / account lifecycle ──────────────────────────────────────────

    def signup(self) -> None:
        """Create a fresh guest account. Sets viewer_id and auth_key."""
        self._regen_sid()
        self.call("tool/pre_signup")
        time.sleep(0.9)
        self._regen_sid()
        res = self.call(
            "tool/signup",
            {
                "error_code": 0,
                "error_message": "",
                "attestation_type": 0,
                "optin_user_birth": 199801,
                "dma_state": 0,
                "country": "Canada",
                "credential": "",
            },
        )
        d = res.get("data", {})
        if d.get("viewer_id"):
            self.viewer_id = d["viewer_id"]
        if d.get("auth_key"):
            self.auth_key_hex = base64.b64decode(d["auth_key"]).hex()

    def refresh_steam_ticket(self) -> None:
        """Regenerate Steam session ticket from stored credentials."""
        if not self.steam_username or not self.steam_password:
            raise RuntimeError(
                "steam_username / steam_password not set — "
                "add them to the account config or STEAM_USERNAME / STEAM_PASSWORD env vars"
            )
        log.info("Refreshing Steam session ticket for %s...", self.steam_username)
        self.steam_id, self.steam_ticket = get_steam_ticket(
            self.steam_username, self.steam_password
        )
        log.info("Steam ticket refreshed (steam_id=%s)", self.steam_id)

    def login(self) -> None:
        """Full login sequence. Refreshes Steam ticket then signs up (if needed) + start_session + load/index."""
        self.refresh_steam_ticket()
        if not self.auth_key_hex:
            self.signup()
        self._regen_sid()
        self.call("tool/start_session", {"attestation_type": 0, "device_token": None})
        self.call("load/index", {"adid": ""})

    def to_config(self) -> dict:
        return {
            "viewer_id": self.viewer_id,
            "udid": self.udid,
            "auth_key": self.auth_key_hex,
            "steam_id": self.steam_id,
            "steam_session_ticket": self.steam_ticket,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "graphics_device_name": self.graphics_device,
            "platform_os_version": self.platform_os,
            "locale": self.locale,
            "unity_ver": self.unity_ver,
            "app_ver": self.app_ver,
            "res_ver": self.res_ver,
        }

    @classmethod
    def from_config_file(cls, path: str | Path) -> "UmaClient":
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        return cls(cfg)

    def save_config(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_config(), f, indent=2)
        log.info("Config saved to %s", path)

    # ── Friend / social API ───────────────────────────────────────────────

    def friend_search(self, viewer_id: int) -> dict:
        """Fetch a player's public profile by viewer_id."""
        return self.call(
            "friend/search",
            {"friend_viewer_id": viewer_id, "deleted_response_type": 0},
        )

    def friend_recommend(self, exclude: list[int] | None = None) -> dict:
        """Get the server's recommended friend list (free discovery)."""
        payload: dict[str, Any] = {}
        if exclude:
            payload["exclude_viewer_id_array"] = exclude
        return self.call("friend/renew_recommend_list", payload)

    def pre_single_mode(self, exclude: list[int] | None = None) -> dict:
        """Pre-career screen — returns available borrow support cards."""
        payload: dict[str, Any] = {}
        if exclude:
            payload["exclude_viewer_id_array"] = exclude
        return self.call("pre_single_mode/index", payload)
