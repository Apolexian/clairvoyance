// dump_db_key.js
// Hooks Sqlite3MC.Key_SetBytes (il2cpp) and sqlite3_key (native) to capture
// the meta DB decryption key when the game opens the meta database.
//
// Usage: python3 dump_db_key.py  (game must be running)
(function () {
    "use strict";

    // ── IL2CPP helpers (inline minimal subset) ───────────────────────────
    const GA = (function () {
        const NAMES = ["GameAssembly.dll", "GameAssembly", "libil2cpp.so"];
        for (const n of NAMES) {
            try { return Process.getModuleByName(n); } catch (e) {}
        }
        return null;
    })();

    if (!GA) { console.error("[dbkey] GameAssembly not found"); return; }
    console.log(`[dbkey] GameAssembly @ ${GA.base} (${(GA.size / 1024 / 1024).toFixed(0)} MB)`);

    function ex(name) {
        try { return GA.findExportByName(name) || null; } catch (e) { return null; }
    }

    // IL2CPP reflection API
    const il2cpp_domain_get            = new NativeFunction(ex("il2cpp_domain_get"),            "pointer", []);
    const il2cpp_domain_get_assemblies = new NativeFunction(ex("il2cpp_domain_get_assemblies"), "pointer", ["pointer", "pointer"]);
    const il2cpp_assembly_get_image    = new NativeFunction(ex("il2cpp_assembly_get_image"),    "pointer", ["pointer"]);
    const il2cpp_image_get_class_count = new NativeFunction(ex("il2cpp_image_get_class_count"), "uint32",  ["pointer"]);
    const il2cpp_image_get_class       = new NativeFunction(ex("il2cpp_image_get_class"),       "pointer", ["pointer", "uint32"]);
    const il2cpp_class_get_name        = new NativeFunction(ex("il2cpp_class_get_name"),        "pointer", ["pointer"]);
    const il2cpp_class_get_namespace   = new NativeFunction(ex("il2cpp_class_get_namespace"),   "pointer", ["pointer"]);
    const il2cpp_class_get_methods     = new NativeFunction(ex("il2cpp_class_get_methods"),     "pointer", ["pointer", "pointer"]);
    const il2cpp_method_get_name       = new NativeFunction(ex("il2cpp_method_get_name"),       "pointer", ["pointer"]);
    const il2cpp_method_get_param_count= new NativeFunction(ex("il2cpp_method_get_param_count"),"uint32",  ["pointer"]);

    function readStr(ptr) {
        if (!ptr || ptr.isNull()) return "";
        try { return ptr.readUtf8String(); } catch (e) { return ""; }
    }

    function findClass(targetName, targetNs) {
        const domain = il2cpp_domain_get();
        const sizeBuf = Memory.alloc(8);
        const assemblies = il2cpp_domain_get_assemblies(domain, sizeBuf);
        const count = sizeBuf.readU32();

        for (let i = 0; i < count; i++) {
            const asm = assemblies.add(i * Process.pointerSize).readPointer();
            const img = il2cpp_assembly_get_image(asm);
            const cc = il2cpp_image_get_class_count(img);
            for (let j = 0; j < cc; j++) {
                const cls = il2cpp_image_get_class(img, j);
                if (!cls || cls.isNull()) continue;
                const name = readStr(il2cpp_class_get_name(cls));
                if (name !== targetName) continue;
                if (targetNs) {
                    const ns = readStr(il2cpp_class_get_namespace(cls));
                    if (ns !== targetNs) continue;
                }
                return cls;
            }
        }
        return null;
    }

    function getMethods(cls) {
        const iter = Memory.alloc(Process.pointerSize).writePointer(ptr(0));
        const methods = [];
        while (true) {
            const m = il2cpp_class_get_methods(cls, iter);
            if (!m || m.isNull()) break;
            methods.push(m);
        }
        return methods;
    }

    // ── Approach 1: hook Sqlite3MC.Key_SetBytes at il2cpp level ─────────
    function hookIl2cpp() {
        console.log("[dbkey] Searching for Sqlite3MC class...");
        const cls = findClass("Sqlite3MC");
        if (!cls || cls.isNull()) {
            console.log("[dbkey] Sqlite3MC class not found (may be obfuscated)");
            return false;
        }
        console.log("[dbkey] Found Sqlite3MC class");

        const methods = getMethods(cls);
        let hooked = 0;
        for (const m of methods) {
            const name = readStr(il2cpp_method_get_name(m));
            if (name.toLowerCase().includes("key") || name.toLowerCase().includes("setkey")) {
                console.log(`[dbkey] Found method: Sqlite3MC.${name} (${il2cpp_method_get_param_count(m)} params)`);
                // Method pointer is at offset 0 in MethodInfo struct
                const fnPtr = m.readPointer();
                try {
                    Interceptor.attach(fnPtr, {
                        onEnter(args) {
                            // Key_SetBytes(IntPtr db, byte[] keyBytes)
                            // args[0] = this (static → null), args[1] = db ptr, args[2] = byte[] managed array
                            // In il2cpp, a byte[] is: [vtable][monitor][length][data...]
                            try {
                                const arrPtr = args[2];
                                const len = arrPtr.add(Process.pointerSize * 2).readS32();
                                if (len <= 0 || len > 256) return;
                                const data = arrPtr.add(Process.pointerSize * 2 + 4).readByteArray(len);
                                const hex = Array.from(new Uint8Array(data))
                                    .map(b => b.toString(16).padStart(2, '0')).join('');
                                console.log(`\n${"=".repeat(60)}`);
                                console.log(`[KEY] Sqlite3MC.${name} called`);
                                console.log(`  length = ${len}`);
                                console.log(`  hex    = ${hex}`);
                                console.log(`  bytes  = [${Array.from(new Uint8Array(data)).map(b => '0x' + b.toString(16).toUpperCase().padStart(2,'0')).join(', ')}]`);
                                console.log(`${"=".repeat(60)}\n`);
                                send({ type: "db_key", method: `Sqlite3MC.${name}`, nKey: len, key: hex });
                            } catch (e) {
                                console.log(`[dbkey] Key_SetBytes hook error: ${e}`);
                            }
                        }
                    });
                    hooked++;
                } catch (e) {
                    console.log(`[dbkey] Failed to hook ${name}: ${e}`);
                }
            }
        }
        return hooked > 0;
    }

    // ── Approach 2: hook UmaDatabaseController constructor ──────────────
    function hookDbController() {
        console.log("[dbkey] Searching for UmaDatabaseController...");
        const cls = findClass("UmaDatabaseController");
        if (!cls || cls.isNull()) {
            console.log("[dbkey] UmaDatabaseController not found (obfuscated?)");
            return false;
        }

        const methods = getMethods(cls);
        let hooked = 0;
        for (const m of methods) {
            const name = readStr(il2cpp_method_get_name(m));
            if (name === ".ctor" || name === "GenFinalKey") {
                console.log(`[dbkey] Hooking UmaDatabaseController.${name}`);
                const fnPtr = m.readPointer();
                try {
                    Interceptor.attach(fnPtr, {
                        onEnter(args) {
                            console.log(`[dbkey] UmaDatabaseController.${name} called`);
                        },
                        onLeave(retval) {
                            if (name === "GenFinalKey") {
                                // returns byte[] — the final derived key
                                try {
                                    const arrPtr = retval;
                                    if (!arrPtr || arrPtr.isNull()) return;
                                    const len = arrPtr.add(Process.pointerSize * 2).readS32();
                                    if (len <= 0 || len > 256) return;
                                    const data = arrPtr.add(Process.pointerSize * 2 + 4).readByteArray(len);
                                    const hex = Array.from(new Uint8Array(data))
                                        .map(b => b.toString(16).padStart(2, '0')).join('');
                                    console.log(`\n${"=".repeat(60)}`);
                                    console.log(`[KEY] GenFinalKey returned:`);
                                    console.log(`  length = ${len}`);
                                    console.log(`  hex    = ${hex}`);
                                    console.log(`  bytes  = [${Array.from(new Uint8Array(data)).map(b => '0x' + b.toString(16).toUpperCase().padStart(2,'0')).join(', ')}]`);
                                    console.log(`${"=".repeat(60)}\n`);
                                    send({ type: "db_key", method: "GenFinalKey", nKey: len, key: hex });
                                } catch (e) {
                                    console.log(`[dbkey] GenFinalKey hook error: ${e}`);
                                }
                            }
                        }
                    });
                    hooked++;
                } catch (e) {
                    console.log(`[dbkey] Failed to hook ${name}: ${e}`);
                }
            }
        }
        return hooked > 0;
    }

    // ── Approach 3: scan for native sqlite3_key in all loaded modules ────
    function hookNativeSqlite3Key() {
        console.log("[dbkey] Scanning all modules for sqlite3_key export...");
        Process.enumerateModules().forEach(mod => {
            try {
                const addr = mod.findExportByName("sqlite3_key");
                if (addr) {
                    console.log(`[dbkey] Found sqlite3_key in ${mod.name} @ ${addr}`);
                    Interceptor.attach(addr, {
                        onEnter(args) {
                            const nKey = args[2].toInt32();
                            if (nKey <= 0 || nKey > 256) return;
                            const hex = Array.from(new Uint8Array(args[1].readByteArray(nKey)))
                                .map(b => b.toString(16).padStart(2, '0')).join('');
                            console.log(`\n${"=".repeat(60)}`);
                            console.log(`[KEY] sqlite3_key in ${mod.name}`);
                            console.log(`  nKey = ${nKey}, key = ${hex}`);
                            console.log(`${"=".repeat(60)}\n`);
                            send({ type: "db_key", method: `sqlite3_key@${mod.name}`, nKey, key: hex });
                        }
                    });
                }
            } catch (e) {}
        });
    }

    hookIl2cpp();
    hookDbController();
    hookNativeSqlite3Key();

    console.log("[dbkey] Hooks installed. Waiting for game to open meta DB...");
    console.log("[dbkey] Tip: restart the game if it already opened meta.");
})();
