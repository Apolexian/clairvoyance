"""
Capture the raw start_session and load/index request payloads from the running game.
Run, then tap something on the home screen.
"""
import sys, time, json, base64, struct, hashlib, os
import frida
from pathlib import Path

_JS_DIR = Path(__file__).parent / "js"

_JS = r"""
(function() {
    var targets = ["tool/start_session", "load/index"];
    var captured = {};
    var _bufs = Object.create(null);

    function b64(s) {
        var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        var out = [], buf = 0, bits = 0;
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i); if (c === "=") break;
            var idx = chars.indexOf(c); if (idx < 0) continue;
            buf = (buf << 6) | idx; bits += 6;
            if (bits >= 8) { bits -= 8; out.push((buf >> bits) & 255); }
        }
        return out;
    }

    function toHex(arr, s, e) {
        var h = "";
        for (var i = s; i < e; i++) { var b = arr[i].toString(16); h += b.length < 2 ? "0"+b : b; }
        return h;
    }

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
            for (var i = 0; i < targets.length; i++) {
                if (headers.indexOf(targets[i]) >= 0) { ep = targets[i]; break; }
            }

            if (!ep || captured[ep]) { pos = bodyStart; continue; }

            var clM = headers.match(/Content-Length:\s*(\d+)/i);
            if (!clM) { pos = bodyStart; continue; }
            var bodyEnd = bodyStart + parseInt(clM[1]);
            if (buf.length < bodyEnd) break;

            var body = buf.slice(bodyStart, bodyEnd).trim();
            var vidM = headers.match(/ViewerID:\s*(\d+)/i);
            var sidM = headers.match(/SID:\s*([0-9a-f]+)/i);

            captured[ep] = true;
            send({ type: "payload", ep: ep, body: body,
                   viewer_id: vidM ? vidM[1] : null,
                   sid: sidM ? sidM[1] : null });
            pos = bodyEnd;
        }
        _bufs[key] = buf.slice(Math.max(0, buf.length - 8192));
    }

    function attachWrite(addr) {
        Interceptor.attach(addr, {
            onEnter: function(args) {
                var len = args[2].toInt32();
                if (len <= 0 || len > 1048576) return;
                try {
                    var bytes = args[1].readByteArray(len);
                    var u8 = new Uint8Array(bytes);
                    var s = ""; for (var i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
                    feedChunk(args[0].toString(), s);
                } catch(e) {}
            }
        });
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

def get_iv(udid):
    return udid.replace('-','').lower()[:16].encode()

def dump_blob1(body_b64):
    """Print the blob1 header fields the game sends."""
    try:
        raw = base64.b64decode(body_b64)
        hl = struct.unpack('<I', raw[:4])[0]
        blob1 = raw[4:4+hl]
        # HEAD(52) sid(16) udid(16) response_key(32) auth_key(rest)
        head = blob1[:52]
        sid = blob1[52:68]
        udid_raw = blob1[68:84]
        rkey = blob1[84:116]
        auth = blob1[116:]
        print(f"  [blob1] len={hl}")
        print(f"  [blob1] sid       = {sid.hex()}")
        print(f"  [blob1] udid      = {udid_raw.hex()}")
        print(f"  [blob1] resp_key  = {rkey.hex()}")
        print(f"  [blob1] auth_key  = {auth.hex()}  (len={len(auth)})")
    except Exception as e:
        print(f"  [blob1 dump failed: {e}]")

def try_decrypt(body_b64, udid):
    try:
        raw = base64.b64decode(body_b64)
        # skip blob1 header
        hl = struct.unpack('<I', raw[:4])[0]
        cipher_part = raw[4+hl:]
        key = cipher_part[-32:]
        ct = cipher_part[:-32]
        iv = get_iv(udid)
        pt = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), 16)
        size = struct.unpack('<I', pt[:4])[0]
        return msgpack.unpackb(pt[4:4+size], raw=False, strict_map_key=False)
    except Exception as e:
        return {"error": str(e)}

def main():
    session = None
    for name in ["UmamusumePrettyDerby.exe", "UmamusumePrettyDerby"]:
        try: session = frida.attach(name); break
        except frida.ProcessNotFoundError: pass
    if not session:
        print("Game not found."); sys.exit(1)
    print("Attached. Tap something on the home screen...")

    captured = {}
    udid = None
    try:
        cfg = json.load(open("crawler_accounts/account_0.json"))
        udid = cfg.get("udid","")
    except: pass

    def on_message(msg, _data):
        if msg.get("type") != "send": return
        p = msg.get("payload") or {}
        if p.get("type") == "ready":
            print(f"Hooked {p['hooked']} endpoints")
        elif p.get("type") == "payload":
            ep = p["ep"]
            print(f"\n=== {ep} ===")
            print(f"ViewerID header : {p.get('viewer_id')}")
            print(f"SID header      : {p.get('sid')}")
            dump_blob1(p["body"])
            if udid:
                dec = try_decrypt(p["body"], udid)
                for k, v in dec.items():
                    if k == "steam_session_ticket" and v:
                        v = str(v)[:32] + "..."
                    print(f"  {k}: {v}")
                # save full ticket to account config
                if "steam_session_ticket" in dec and ep == "tool/start_session":
                    try:
                        cfg_path = "crawler_accounts/account_0.json"
                        cfg = json.load(open(cfg_path))
                        cfg["steam_session_ticket"] = dec["steam_session_ticket"]
                        cfg["steam_id"] = str(dec.get("steam_id", cfg.get("steam_id","")))
                        json.dump(cfg, open(cfg_path,"w"), indent=2)
                        print(f"  [saved steam_session_ticket to {cfg_path}]")
                    except Exception as e:
                        print(f"  [save failed: {e}]")
            captured[ep] = True

    helpers = (_JS_DIR / "il2cpp_helpers.js").read_text(encoding="utf-8")
    script = session.create_script(helpers + "\n" + _JS, runtime="v8")
    script.on("message", on_message)
    script.load()

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if len(captured) >= 2: break
        time.sleep(0.2)

    script.unload()
    session.detach()

if __name__ == "__main__":
    main()
