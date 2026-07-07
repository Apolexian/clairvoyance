"""
Sniff APP-VER, RES-VER, viewer_id, udid, and auth_key from the running game.
Run while the game is open and tap something to trigger a network request.

Saves:
  versions.json          — app_ver + res_ver
  crawler_accounts/account_0.json  — full account credentials for the crawler
"""

import json
import sys
import time
from pathlib import Path

import frida

_JS_DIR = Path(__file__).parent / "js"

_EXTRACTOR_JS = r"""
(function() {
    var captured = {};

    // ── b64 decode ────────────────────────────────────────────────────────
    function b64(s) {
        var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        var out = [], buf = 0, bits = 0;
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i);
            if (c === "=") break;
            var idx = chars.indexOf(c);
            if (idx < 0) continue;
            buf = (buf << 6) | idx; bits += 6;
            if (bits >= 8) { bits -= 8; out.push((buf >> bits) & 255); }
        }
        return out;
    }

    function toHex(arr, start, end) {
        var h = "";
        for (var i = start; i < end; i++) {
            var b = arr[i].toString(16);
            h += b.length < 2 ? "0" + b : b;
        }
        return h;
    }

    function uuidFromHex(h) {
        return h.slice(0,8)+"-"+h.slice(8,12)+"-"+h.slice(12,16)+"-"+h.slice(16,20)+"-"+h.slice(20,32);
    }

    // Extract creds from blob1 tail: session_id(16) + udid(16) + response_key(32) + auth_key(48)
    function extractCreds(bodyStr) {
        try {
            var decoded = b64(bodyStr.trim());
            if (decoded.length < 170) return null;
            var headerLen = decoded[0]|(decoded[1]<<8)|(decoded[2]<<16)|(decoded[3]<<24);
            var blob1End = 4 + headerLen;
            if (headerLen < 120 || headerLen > 2048 || decoded.length < blob1End) return null;
            // udid: blob1End - 96 to blob1End - 80
            var udidHex = toHex(decoded, blob1End - 96, blob1End - 80);
            // auth_key: last 48 bytes of blob1
            var authHex = toHex(decoded, blob1End - 48, blob1End);
            if (udidHex.length !== 32 || authHex.length < 64) return null;
            return { udid: uuidFromHex(udidHex), auth_key: authHex };
        } catch(e) { return null; }
    }

    // ── HTTP chunk reassembly ─────────────────────────────────────────────
    var _bufs = Object.create(null);

    function feedChunk(connKey, chunk) {
        var buf = (_bufs[connKey] || "") + chunk;
        if (buf.length > 2097152) buf = buf.slice(-1048576);

        var start = buf.indexOf("POST ");
        if (start < 0) { _bufs[connKey] = buf.slice(-4096); return; }
        buf = buf.slice(start);

        var headerEnd = buf.indexOf("\r\n\r\n");
        if (headerEnd < 0) { _bufs[connKey] = buf; return; }

        var headers = buf.slice(0, headerEnd);
        var bodyStart = headerEnd + 4;

        var appM  = headers.match(/APP-VER:\s*([^\r\n]+)/i);
        var resM  = headers.match(/RES-VER:\s*([^\r\n]+)/i);
        var vidM  = headers.match(/ViewerID:\s*(\d+)/i);

        if (appM && !captured.app_ver) captured.app_ver = appM[1].trim();
        if (resM && !captured.res_ver) captured.res_ver = resM[1].trim();
        if (vidM && !captured.viewer_id) captured.viewer_id = parseInt(vidM[1], 10);

        // Try to extract auth from body
        if (!captured.auth_key) {
            // Determine body length from Content-Length header
            var clM = headers.match(/Content-Length:\s*(\d+)/i);
            var bodyEnd = clM ? bodyStart + parseInt(clM[1], 10) : buf.length;
            var body = buf.slice(bodyStart, bodyEnd).trim();
            if (body.length > 100) {
                var creds = extractCreds(body);
                if (creds) {
                    captured.udid     = creds.udid;
                    captured.auth_key = creds.auth_key;
                }
            }
        }

        _bufs[connKey] = buf.slice(bodyStart);

        if (captured.app_ver && captured.res_ver && captured.viewer_id && captured.auth_key) {
            send({type: "captured", data: captured});
        }
    }

    function attachWrite(addr) {
        Interceptor.attach(addr, {
            onEnter: function(args) {
                var len = args[2].toInt32();
                if (len <= 0 || len > 1048576) return;
                try {
                    var bytes = args[1].readByteArray(len);
                    var u8 = new Uint8Array(bytes);
                    var s = "";
                    for (var i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
                    feedChunk(args[0].toString(), s);
                } catch(e) {}
            }
        });
    }

    var hooked = 0;

    // 1. SSL_write global
    try {
        var addr = Module.findExportByName(null, "SSL_write");
        if (addr) { attachWrite(addr); hooked++; }
    } catch(e) {}

    // 2. UnityTLS vtable
    try {
        var ga = Process.findModuleByName("GameAssembly.dll") || Process.findModuleByName("libil2cpp.so");
        if (ga) {
            var installFn = ga.findExportByName("il2cpp_unity_install_unitytls_interface");
            if (installFn) {
                var rb = new Uint8Array(installFn.readByteArray(16));
                var realFn = installFn;
                if (rb[0] === 0xe9) {
                    var off = rb[1]|(rb[2]<<8)|(rb[3]<<16)|(rb[4]<<24);
                    if (off > 0x7fffffff) off -= 0x100000000;
                    realFn = installFn.add(5 + off);
                    rb = new Uint8Array(realFn.readByteArray(16));
                }
                if (rb[0] === 0x48 && rb[1] === 0x89 && rb[2] === 0x0d) {
                    var disp = rb[3]|(rb[4]<<8)|(rb[5]<<16)|(rb[6]<<24);
                    if (disp > 0x7fffffff) disp -= 0x100000000;
                    var globalPtr = realFn.add(7 + disp);
                    var iface = globalPtr.readPointer();
                    if (iface && !iface.isNull()) {
                        var seen = Object.create(null);
                        [0xd0, 0xd8, 0xe0, 0xe8].forEach(function(off) {
                            var fn = iface.add(off).readPointer();
                            if (!fn || fn.isNull()) return;
                            var k = fn.toString();
                            if (seen[k]) return;
                            seen[k] = true;
                            try { attachWrite(fn); hooked++; } catch(e) {}
                        });
                    }
                }
            }
        }
    } catch(e) {}

    // 3. SChannel EncryptMessage
    try {
        var secur32 = Process.getModuleByName("secur32.dll");
        var encFn = secur32 && secur32.findExportByName("EncryptMessage");
        if (encFn) {
            Interceptor.attach(encFn, {
                onEnter: function(args) {
                    try {
                        var bufDesc = args[1];
                        var cBufs = bufDesc.add(4).readU32();
                        var pBufs = bufDesc.add(8).readPointer();
                        var ps = Process.pointerSize;
                        var stride = 4 + 4 + ps;
                        for (var i = 0; i < cBufs && i < 4; i++) {
                            var e = pBufs.add(i * stride);
                            var cb = e.readU32(), bt = e.add(4).readU32();
                            if (bt !== 1 || cb <= 0 || cb > 65536) continue;
                            var pv = e.add(8).readPointer();
                            var bytes = pv.readByteArray(Math.min(cb, 4096));
                            var u8 = new Uint8Array(bytes);
                            var s = "";
                            for (var j = 0; j < u8.length; j++) s += String.fromCharCode(u8[j]);
                            feedChunk("schannel", s);
                            break;
                        }
                    } catch(e) {}
                }
            });
            hooked++;
        }
    } catch(e) {}

    send({type: "ready", hooked: hooked});
})();
"""

OUT_VERSIONS = Path(__file__).parent / "versions.json"
OUT_ACCOUNT  = Path(__file__).parent / "crawler_accounts" / "account_0.json"
PROCESS_NAMES = ["UmamusumePrettyDerby.exe", "UmamusumePrettyDerby"]
TIMEOUT = 120


def _load_js() -> str:
    helpers = (_JS_DIR / "il2cpp_helpers.js").read_text(encoding="utf-8")
    return helpers + "\n" + _EXTRACTOR_JS


def main() -> None:
    print("Attaching to game process...")
    session = None
    for name in PROCESS_NAMES:
        try:
            session = frida.attach(name)
            print(f"Attached to {name}")
            break
        except frida.ProcessNotFoundError:
            pass
        except Exception as e:
            print(f"  {name}: {e}")

    if session is None:
        print("ERROR: Game not found.")
        sys.exit(1)

    result: dict = {}

    def on_message(msg: dict, _data: object) -> None:
        if msg.get("type") == "error":
            print(f"JS error: {msg.get('description')} @ {msg.get('fileName')}:{msg.get('lineNumber')}")
            return
        if msg.get("type") != "send":
            return
        payload = msg.get("payload") or {}
        t = payload.get("type")
        if t == "ready":
            n = payload.get("hooked", 0)
            print(f"Hooked {n} TLS write endpoint(s)")
            print("Tap something in-game to trigger a network request...")
        elif t == "captured":
            result.update(payload.get("data", {}))

    script = session.create_script(_load_js(), runtime="v8")
    script.on("message", on_message)
    script.load()

    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        if result.get("auth_key") and result.get("app_ver"):
            break
        if result.get("app_ver") and not result.get("auth_key"):
            # Got versions but not creds yet — keep waiting
            pass
        time.sleep(0.2)

    script.unload()
    session.detach()

    if not result.get("app_ver"):
        print(f"Nothing captured in {TIMEOUT}s.")
        sys.exit(1)

    # Save versions.json
    versions = {"app_ver": result["app_ver"], "res_ver": result["res_ver"]}
    OUT_VERSIONS.write_text(json.dumps(versions, indent=2), encoding="utf-8")
    print(f"\nAPP-VER : {result['app_ver']}")
    print(f"RES-VER : {result['res_ver']}")
    print(f"Saved → {OUT_VERSIONS}")

    if result.get("auth_key") and result.get("viewer_id"):
        account = {
            "viewer_id":   result["viewer_id"],
            "udid":        result.get("udid", ""),
            "auth_key":    result["auth_key"],
            "app_ver":     result["app_ver"],
            "res_ver":     result["res_ver"],
            "steam_id":    "",
            "steam_session_ticket": "",
        }
        OUT_ACCOUNT.parent.mkdir(parents=True, exist_ok=True)
        OUT_ACCOUNT.write_text(json.dumps(account, indent=2), encoding="utf-8")
        print(f"\nviewer_id : {result['viewer_id']}")
        print(f"udid      : {result.get('udid', '(not captured)')}")
        print(f"auth_key  : {result['auth_key'][:16]}...")
        print(f"Saved → {OUT_ACCOUNT}")
    else:
        print("\nVersions captured but credentials incomplete — tap more in-game and retry.")


if __name__ == "__main__":
    main()
