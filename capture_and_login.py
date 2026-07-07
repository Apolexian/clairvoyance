"""
Capture the full load/index payload from the running game (all device fields,
viewer_id, auth_key from blob1, and the live Steam ticket), then immediately
attempt a headless login in the same process — before the ticket expires.

Mirrors sweepy's approach: use the GAME's exact device profile + captured ticket,
no regenerated fields.

Run with the game open on the home screen, then tap something.
"""
import sys, time, json, base64, struct
from pathlib import Path
import frida

_JS_DIR = Path(__file__).parent / "js"

_JS = r"""
(function() {
    var targets = ["load/index", "tool/start_session"];
    var captured = {};
    var _bufs = Object.create(null);

    function feedChunk(key, chunk) {
        var buf = (_bufs[key] || "") + chunk;
        if (buf.length > 4194304) buf = buf.slice(-2097152);
        var pos = 0;
        while (true) {
            var start = buf.indexOf("POST ", pos);
            if (start < 0) break;
            var headerEnd = buf.indexOf("\r\n\r\n", start);
            if (headerEnd < 0) break;
            var headers = buf.slice(start, headerEnd);
            var bodyStart = headerEnd + 4;
            var ep = null;
            for (var i = 0; i < targets.length; i++)
                if (headers.indexOf(targets[i]) >= 0) { ep = targets[i]; break; }
            if (!ep || captured[ep]) { pos = bodyStart; continue; }
            var clM = headers.match(/Content-Length:\s*(\d+)/i);
            if (!clM) { pos = bodyStart; continue; }
            var bodyEnd = bodyStart + parseInt(clM[1]);
            if (buf.length < bodyEnd) break;
            captured[ep] = true;
            send({ type: "payload", ep: ep, body: buf.slice(bodyStart, bodyEnd).trim() });
            pos = bodyEnd;
        }
        _bufs[key] = buf.slice(Math.max(0, buf.length - 8192));
    }

    function attachWrite(addr) {
        Interceptor.attach(addr, { onEnter: function(args) {
            var len = args[2].toInt32();
            if (len <= 0 || len > 1048576) return;
            try {
                var u8 = new Uint8Array(args[1].readByteArray(len));
                var s = ""; for (var i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
                feedChunk(args[0].toString(), s);
            } catch(e) {}
        }});
    }

    var hooked = 0;
    try { var a = Module.findExportByName(null,"SSL_write"); if(a){attachWrite(a);hooked++;} } catch(e){}
    try {
        var ga = Process.findModuleByName("GameAssembly.dll");
        if (ga) {
            var fn = ga.findExportByName("il2cpp_unity_install_unitytls_interface");
            if (fn) {
                var rb = new Uint8Array(fn.readByteArray(16)), rf = fn;
                if (rb[0]===0xe9) { var o=rb[1]|(rb[2]<<8)|(rb[3]<<16)|(rb[4]<<24); if(o>0x7fffffff)o-=0x100000000; rf=fn.add(5+o); rb=new Uint8Array(rf.readByteArray(16)); }
                if (rb[0]===0x48&&rb[1]===0x89&&rb[2]===0x0d) {
                    var d=rb[3]|(rb[4]<<8)|(rb[5]<<16)|(rb[6]<<24); if(d>0x7fffffff)d-=0x100000000;
                    var gp=rf.add(7+d), iface=gp.readPointer();
                    if(iface&&!iface.isNull()){
                        var seen=Object.create(null);
                        [0xd0,0xd8,0xe0,0xe8].forEach(function(off){
                            var f=iface.add(off).readPointer(); if(!f||f.isNull()) return;
                            var k=f.toString(); if(seen[k]) return; seen[k]=true;
                            try{attachWrite(f);hooked++;}catch(e){}
                        });
                    }
                }
            }
        }
    } catch(e){}
    send({type:"ready", hooked:hooked});
})();
"""

import msgpack
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def get_udid_from_blob1(body_b64):
    raw = base64.b64decode(body_b64)
    hl = struct.unpack('<I', raw[:4])[0]
    blob1 = raw[4:4+hl]
    udid_raw = blob1[52+16:52+32]  # after HEAD(52)+sid(16)
    h = udid_raw.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def decrypt_payload(body_b64, udid):
    raw = base64.b64decode(body_b64)
    hl = struct.unpack('<I', raw[:4])[0]
    cipher_part = raw[4+hl:]
    key = cipher_part[-32:]
    ct = cipher_part[:-32]
    iv = udid.replace('-', '').lower()[:16].encode()
    pt = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), 16)
    size = struct.unpack('<I', pt[:4])[0]
    return msgpack.unpackb(pt[4:4+size], raw=False, strict_map_key=False)


def get_auth_from_blob1(body_b64):
    raw = base64.b64decode(body_b64)
    hl = struct.unpack('<I', raw[:4])[0]
    blob1 = raw[4:4+hl]
    return blob1[116:].hex()  # auth_key tail


def main():
    sys.path.insert(0, str(Path(__file__).parent))

    session = None
    for name in ["UmamusumePrettyDerby.exe", "UmamusumePrettyDerby"]:
        try: session = frida.attach(name); break
        except frida.ProcessNotFoundError: pass
    if not session:
        print("Game not found."); sys.exit(1)
    print("Attached. Tap something on the home screen...")

    result = {}

    def on_message(msg, _data):
        if msg.get("type") != "send": return
        p = msg.get("payload") or {}
        if p.get("type") == "ready":
            print(f"Hooked {p['hooked']} endpoints")
        elif p.get("type") == "payload" and p["ep"] == "load/index":
            body = p["body"]
            udid = get_udid_from_blob1(body)
            dec = decrypt_payload(body, udid)
            result["cfg"] = {
                "viewer_id": dec.get("viewer_id"),
                "udid": udid,
                "auth_key": get_auth_from_blob1(body),
                "device_id": dec.get("device_id"),
                "device_name": dec.get("device_name"),
                "graphics_device_name": dec.get("graphics_device_name"),
                "ip_address": dec.get("ip_address"),
                "platform_os_version": dec.get("platform_os_version"),
                "locale": dec.get("locale", "JPN"),
                "steam_id": str(dec.get("steam_id", "")),
                "steam_session_ticket": dec.get("steam_session_ticket", ""),
                "app_ver": "1.22.1",
                "res_ver": "10006400",
            }
            print(f"Captured viewer_id={result['cfg']['viewer_id']} "
                  f"device_id={result['cfg']['device_id'][:12]}... "
                  f"ticket_len={len(result['cfg']['steam_session_ticket'])}")

    helpers = (_JS_DIR / "il2cpp_helpers.js").read_text(encoding="utf-8")
    script = session.create_script(helpers + "\n" + _JS, runtime="v8")
    script.on("message", on_message)
    script.load()

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and "cfg" not in result:
        time.sleep(0.1)
    script.unload()
    session.detach()

    if "cfg" not in result:
        print("Did not capture load/index. Try tapping more in-game.")
        sys.exit(1)

    cfg = result["cfg"]
    Path("crawler_accounts").mkdir(exist_ok=True)
    json.dump(cfg, open("crawler_accounts/account_0.json", "w"), indent=2)
    print("Saved full config. Attempting headless login NOW (ticket is fresh)...")

    # immediate headless login with the EXACT captured ticket — no regen
    from crawler.client import UmaClient
    c = UmaClient(cfg)
    c._regen_sid()
    c.call("tool/start_session", {"attestation_type": 0, "device_token": None})
    print("start_session OK")
    res = c.call("load/index", {"adid": ""})
    vid = res.get("data_headers", {}).get("viewer_id")
    print(f"load/index OK — viewer_id: {vid}")
    if vid == cfg["viewer_id"]:
        print(">>> SUCCESS: headless login resolves to the SAME account <<<")
    else:
        print(f">>> MISMATCH: expected {cfg['viewer_id']}, got {vid} <<<")


if __name__ == "__main__":
    main()
