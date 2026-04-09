// hook_network.js
// Captures game-server API traffic via two layers:
//
// Layer 1: SSL_read / SSL_write — hooks the TLS library to capture raw
//          decrypted HTTP traffic (request + response bytes). Works
//          regardless of the game's HTTP/serialisation stack.
//
// Layer 2: MsgPack Formatters — hooks Gallop.MsgPack.Formatters.*.Serialize
//          and *.Deserialize methods at the il2cpp level. Gives us the
//          class name of each request/response so we know *what* API call
//          is happening (e.g. SingleModeGainSkillsRequest).
//
// Layer 3: Request/Response Task pipeline — hooks the *Task classes that
//          orchestrate API calls, capturing which endpoint is being called.
//
// Loaded after il2cpp_helpers.js inside a collector IIFE.

(function () {
    "use strict";

    console.log("[network] Initialising network capture...");

    let hookCount = 0;

    // ══════════════════════════════════════════════════════════════════
    // LAYER 1: SSL_read / SSL_write hooks
    // ══════════════════════════════════════════════════════════════════
    //
    // Unity games bundle a TLS library (BoringSSL/OpenSSL). We scan all
    // loaded modules for SSL_read and SSL_write exports. These operate
    // on plaintext — the data has already been decrypted (read) or is
    // about to be encrypted (write).

    const SSL_EXPORT_NAMES = {
        read: ["SSL_read", "SSL_read_ex"],
        write: ["SSL_write", "SSL_write_ex"],
    };

    // Modules that commonly contain the SSL implementation in Unity games
    const SSL_MODULE_HINTS = [
        "libssl",
        "ssleay32",
        "libcrypto",
        "GameAssembly", // BoringSSL sometimes statically linked
        "libil2cpp", // Linux
        "UnityFramework", // macOS/iOS
        "libcurl", // curl backend
    ];

    function tryFindExport(name) {
        // Try well-known modules first
        for (const hint of SSL_MODULE_HINTS) {
            try {
                const mod =
                    Process.getModuleByName(hint + ".dll") ||
                    Process.getModuleByName(hint + ".so") ||
                    Process.getModuleByName(hint + ".dylib") ||
                    Process.getModuleByName(hint);
                if (!mod) continue;
                const addr = mod.findExportByName(name);
                if (addr) {
                    console.log("[network] Found " + name + " in " + mod.name);
                    return addr;
                }
            } catch (e) {}
        }

        // Fallback: search all modules
        try {
            const addr = Module.findExportByName(null, name);
            if (addr) {
                console.log("[network] Found " + name + " (global search)");
                return addr;
            }
        } catch (e) {}

        return null;
    }

    // ── SSL_read: capture server → game (response) data ───────────────

    var sslReadAddr = null;
    for (const name of SSL_EXPORT_NAMES.read) {
        sslReadAddr = tryFindExport(name);
        if (sslReadAddr) break;
    }

    if (sslReadAddr) {
        try {
            Interceptor.attach(sslReadAddr, {
                onEnter: function (args) {
                    this.ssl = args[0];
                    this.buf = args[1];
                    this.num = args[2].toInt32();
                },
                onLeave: function (retval) {
                    var bytesRead = retval.toInt32();
                    if (bytesRead <= 0) return;

                    // Cap at 32KB to avoid sending huge blobs
                    var captureLen = Math.min(bytesRead, 32768);
                    try {
                        var data = this.buf.readByteArray(captureLen);
                        send(
                            {
                                type: "collect",
                                domain: "network",
                                data: {
                                    event: "ssl_read",
                                    bytes: bytesRead,
                                    captured: captureLen,
                                    truncated: bytesRead > captureLen,
                                },
                            },
                            data,
                        );
                    } catch (e) {}
                },
            });
            hookCount++;
            console.log("[network] Hooked SSL_read");
        } catch (e) {
            console.log("[network] Failed to hook SSL_read: " + e);
        }
    } else {
        console.log("[network] SSL_read not found — trying alternative TLS hooks...");

        // Windows fallback: Schannel (DecryptMessage / EncryptMessage)
        try {
            var secur32 = Process.getModuleByName("secur32.dll");
            if (secur32) {
                var decryptMsg = secur32.findExportByName("DecryptMessage");
                if (decryptMsg) {
                    Interceptor.attach(decryptMsg, {
                        onEnter: function (args) {
                            this.ctxt = args[0];
                            this.msg = args[1];
                        },
                        onLeave: function (retval) {
                            if (retval.toInt32() !== 0) return; // SEC_E_OK = 0
                            // Try to read the first buffer from the SecBufferDesc
                            try {
                                var bufDesc = this.msg;
                                var cBuffers = bufDesc.add(4).readU32();
                                var pBuffers = bufDesc.add(8).readPointer();
                                // Each SecBuffer is 12 bytes (cbBuffer:4, BufferType:4, pvBuffer:ptr)
                                // On 64-bit the struct is padded, so use: 4 + 4 + ptrSize
                                var secBufSize = 4 + 4 + Process.pointerSize;
                                for (var i = 0; i < cBuffers && i < 4; i++) {
                                    var bufEntry = pBuffers.add(i * secBufSize);
                                    var cbBuffer = bufEntry.readU32();
                                    var bufType = bufEntry.add(4).readU32();
                                    // SECBUFFER_DATA = 1
                                    if (bufType === 1 && cbBuffer > 0 && cbBuffer < 65536) {
                                        var pvBuffer = bufEntry.add(8).readPointer();
                                        var captureLen = Math.min(cbBuffer, 32768);
                                        var data = pvBuffer.readByteArray(captureLen);
                                        send(
                                            {
                                                type: "collect",
                                                domain: "network",
                                                data: {
                                                    event: "schannel_decrypt",
                                                    bytes: cbBuffer,
                                                    captured: captureLen,
                                                    truncated: cbBuffer > captureLen,
                                                },
                                            },
                                            data,
                                        );
                                        break;
                                    }
                                }
                            } catch (e) {}
                        },
                    });
                    hookCount++;
                    console.log("[network] Hooked Schannel DecryptMessage (fallback)");
                }
            }
        } catch (e) {
            // Not on Windows or secur32 not available
        }
    }

    // ── SSL_write: capture game → server (request) data ───────────────

    var sslWriteAddr = null;
    for (const name of SSL_EXPORT_NAMES.write) {
        sslWriteAddr = tryFindExport(name);
        if (sslWriteAddr) break;
    }

    if (sslWriteAddr) {
        try {
            Interceptor.attach(sslWriteAddr, {
                onEnter: function (args) {
                    var buf = args[1];
                    var num = args[2].toInt32();
                    if (num <= 0) return;

                    var captureLen = Math.min(num, 32768);
                    try {
                        var data = buf.readByteArray(captureLen);
                        send(
                            {
                                type: "collect",
                                domain: "network",
                                data: {
                                    event: "ssl_write",
                                    bytes: num,
                                    captured: captureLen,
                                    truncated: num > captureLen,
                                },
                            },
                            data,
                        );
                    } catch (e) {}
                },
            });
            hookCount++;
            console.log("[network] Hooked SSL_write");
        } catch (e) {
            console.log("[network] Failed to hook SSL_write: " + e);
        }
    } else {
        // Windows fallback: Schannel EncryptMessage
        try {
            var secur32w = Process.getModuleByName("secur32.dll");
            if (secur32w) {
                var encryptMsg = secur32w.findExportByName("EncryptMessage");
                if (encryptMsg) {
                    Interceptor.attach(encryptMsg, {
                        onEnter: function (args) {
                            // Capture the plaintext buffer before encryption
                            try {
                                var bufDesc = args[1];
                                var cBuffers = bufDesc.add(4).readU32();
                                var pBuffers = bufDesc.add(8).readPointer();
                                var secBufSize = 4 + 4 + Process.pointerSize;
                                for (var i = 0; i < cBuffers && i < 4; i++) {
                                    var bufEntry = pBuffers.add(i * secBufSize);
                                    var cbBuffer = bufEntry.readU32();
                                    var bufType = bufEntry.add(4).readU32();
                                    // SECBUFFER_DATA = 1
                                    if (bufType === 1 && cbBuffer > 0 && cbBuffer < 65536) {
                                        var pvBuffer = bufEntry.add(8).readPointer();
                                        var captureLen = Math.min(cbBuffer, 32768);
                                        var data = pvBuffer.readByteArray(captureLen);
                                        send(
                                            {
                                                type: "collect",
                                                domain: "network",
                                                data: {
                                                    event: "schannel_encrypt",
                                                    bytes: cbBuffer,
                                                    captured: captureLen,
                                                    truncated: cbBuffer > captureLen,
                                                },
                                            },
                                            data,
                                        );
                                        break;
                                    }
                                }
                            } catch (e) {}
                        },
                    });
                    hookCount++;
                    console.log("[network] Hooked Schannel EncryptMessage (fallback)");
                }
            }
        } catch (e) {}
    }

    // ══════════════════════════════════════════════════════════════════
    // LAYER 2: MsgPack Formatter hooks (il2cpp)
    // ══════════════════════════════════════════════════════════════════
    //
    // The game has Gallop.MsgPack.Formatters.*Formatter classes, each with
    // Serialize and Deserialize methods. Hooking these tells us the *name*
    // of every API request/response object being serialised.

    console.log("[network] Scanning for MsgPack Formatter classes...");

    var formatterClasses = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        // Match Gallop.MsgPack.Formatters.*Formatter
        if (fullName.indexOf("Gallop.MsgPack.Formatters.") !== 0) return;
        if (!fullName.endsWith("Formatter")) return;

        // Extract the meaningful name (strip namespace + "Formatter" suffix)
        var shortName = fullName.replace("Gallop.MsgPack.Formatters.", "").replace("Formatter", "");
        formatterClasses[fullName] = {
            classPtr: classPtr,
            shortName: shortName,
        };
    });

    var formatterCount = Object.keys(formatterClasses).length;
    console.log("[network] Found " + formatterCount + " MsgPack Formatter classes.");

    // Hook Serialize and Deserialize on each formatter
    var formatterHooks = 0;
    var MAX_FORMATTER_HOOKS = 300; // safety cap

    for (var fqn in formatterClasses) {
        if (formatterHooks >= MAX_FORMATTER_HOOKS) break;

        (function (fqn) {
            var entry = formatterClasses[fqn];
            var info = extractClassInfo(entry.classPtr, fqn);
            var sName = entry.shortName;

            // Hook Serialize
            if (info.methods["Serialize"]) {
                if (
                    hookMethod(info, "Serialize", -1, {
                        onEnter: function () {
                            send({
                                type: "collect",
                                domain: "network",
                                data: {
                                    event: "msgpack_serialize",
                                    formatter: sName,
                                    direction: "request",
                                },
                            });
                        },
                    })
                ) {
                    formatterHooks++;
                }
            }

            // Hook Deserialize
            if (info.methods["Deserialize"]) {
                if (
                    hookMethod(info, "Deserialize", -1, {
                        onEnter: function () {
                            send({
                                type: "collect",
                                domain: "network",
                                data: {
                                    event: "msgpack_deserialize",
                                    formatter: sName,
                                    direction: "response",
                                },
                            });
                        },
                    })
                ) {
                    formatterHooks++;
                }
            }
        })(fqn);
    }

    hookCount += formatterHooks;
    console.log("[network] " + formatterHooks + " MsgPack Formatter hooks installed.");

    // ══════════════════════════════════════════════════════════════════
    // LAYER 3: Task pipeline hooks (il2cpp)
    // ══════════════════════════════════════════════════════════════════
    //
    // The game follows a pattern: FooRequest + FooResponse + FooTask.
    // The Task classes manage the full API lifecycle. We hook their
    // main entry methods to log which API endpoint is being called.

    console.log("[network] Scanning for API Task classes...");

    var taskClasses = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        if (ns !== "Gallop") return;
        if (!name.endsWith("Task")) return;
        // Filter to likely API tasks (those with matching Request/Response)
        // The naming convention is: FooRequest, FooResponse, FooTask
        taskClasses[fullName] = classPtr;
    });

    var taskCount = Object.keys(taskClasses).length;
    console.log("[network] Found " + taskCount + " Task classes.");

    var taskHooks = 0;
    var MAX_TASK_HOOKS = 200;

    for (var taskName in taskClasses) {
        if (taskHooks >= MAX_TASK_HOOKS) break;

        (function (taskName) {
            var taskInfo = extractClassInfo(taskClasses[taskName], taskName);

            // Hook common task lifecycle methods
            var taskMethods = [
                "Start",
                "Execute",
                "SendRequest",
                "OnComplete",
                "OnSuccess",
                "OnError",
                "RunTask",
            ];
            for (var mi = 0; mi < taskMethods.length; mi++) {
                (function (mName) {
                    if (!taskInfo.methods[mName]) return;

                    if (
                        hookMethod(taskInfo, mName, -1, {
                            onEnter: function () {
                                send({
                                    type: "collect",
                                    domain: "network",
                                    data: {
                                        event: "api_task",
                                        task: taskName,
                                        method: mName,
                                    },
                                });
                            },
                        })
                    ) {
                        taskHooks++;
                    }
                })(taskMethods[mi]);
            }
        })(taskName);
    }

    hookCount += taskHooks;
    console.log("[network] " + taskHooks + " Task pipeline hooks installed.");

    // ── Summary ───────────────────────────────────────────────────────

    console.log("[network] Total: " + hookCount + " network hooks installed.");
    send({ type: "hook_status", module: "network", hookCount: hookCount });
})();
