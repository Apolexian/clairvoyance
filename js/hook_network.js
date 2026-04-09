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

                    // Cap at 256KB to capture full race responses
                    var captureLen = Math.min(bytesRead, 262144);
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

                    var captureLen = Math.min(num, 262144);
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

    // Note: Request/Response class lookup is handled by Layer 3's
    // dataClassPtrs / getDataClassInfo. Formatters use the same cache.

    function getReqRespFields(formatterShortName) {
        // formatterShortName is e.g. "Gallop_SingleModeFreeChoiceRewardRequest"
        // Convert to "Gallop.SingleModeFreeChoiceRewardRequest"
        var className = formatterShortName.replace(/_/g, ".");
        // Reuse Layer 3's data class lookup (populated later during setup,
        // but formatter hooks fire at runtime after setup completes)
        var info = getDataClassInfo(className);
        return info ? info.fieldList : null;
    }

    for (var fqn in formatterClasses) {
        if (formatterHooks >= MAX_FORMATTER_HOOKS) break;

        (function (fqn) {
            var entry = formatterClasses[fqn];
            var info = extractClassInfo(entry.classPtr, fqn);
            var sName = entry.shortName;

            // Hook Serialize — reads the value being serialized (request data)
            if (info.methods["Serialize"]) {
                if (
                    hookMethod(info, "Serialize", -1, {
                        onEnter: function (args) {
                            // args: [this, ref writer, value, options]
                            // For instance methods, args[0]=this, args[1]=writer,
                            // args[2]=value (the request/response object), args[3]=options
                            var record = {
                                event: "msgpack_serialize",
                                formatter: sName,
                                direction: "request",
                            };

                            // Try to read fields from the value object
                            try {
                                var valuePtr = args[2];
                                if (valuePtr && !valuePtr.isNull()) {
                                    var fields = getReqRespFields(sName);
                                    if (fields) {
                                        var data = readObjectFields(valuePtr, fields);
                                        if (data) record.fields = data;
                                    }
                                }
                            } catch (e) {}

                            send({
                                type: "collect",
                                domain: "network",
                                data: record,
                            });
                        },
                    })
                ) {
                    formatterHooks++;
                }
            }

            // Hook Deserialize — reads the return value (response data)
            if (info.methods["Deserialize"]) {
                if (
                    hookMethod(info, "Deserialize", -1, {
                        onEnter: function (args) {
                            this._formatterName = sName;
                        },
                        onLeave: function (retval) {
                            var record = {
                                event: "msgpack_deserialize",
                                formatter: this._formatterName,
                                direction: "response",
                            };

                            // Try to read fields from the return value
                            try {
                                if (retval && !retval.isNull()) {
                                    var fields = getReqRespFields(this._formatterName);
                                    if (fields) {
                                        var data = readObjectFields(retval, fields);
                                        if (data) record.fields = data;
                                    }
                                }
                            } catch (e) {}

                            send({
                                type: "collect",
                                domain: "network",
                                data: record,
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
    // LAYER 3: Gallop.*Task API hooks (il2cpp)
    // ══════════════════════════════════════════════════════════════════
    //
    // Every API call in the game is a `Gallop.*Task` class, e.g.
    //   Gallop.SingleModeCheckEventTask
    //   Gallop.SingleModeExecCommandTask
    // They all share the same field layout:
    //   offset 16: postData (byte[])
    //   offset 24: onSuccess callback
    //   offset 32: onError callback
    //   offset 40: headers dict
    //   offset 48: request (Cute.Http.IWebRequest)
    //
    // We scan for ALL Gallop.*Task classes and hook Send + Deserialize
    // on each one. When Send fires, `this` IS the task, so we can read
    // the class name and postData directly.
    //
    // IMPORTANT: Send, Deserialize, and OnError are base-class methods
    // shared across ALL ~300 Task subclasses (same compiled address).
    // hookMethod deduplicates — only ONE callback is installed.
    // We use readClassName(self) at runtime to determine the concrete
    // type, then look up the matching Request/Response class to read
    // its fields dynamically.

    console.log("[network] Scanning for Gallop API Task classes...");

    // Helper: read the il2cpp class name from an object pointer
    function readClassName(objPtr) {
        try {
            var klass = objPtr.readPointer();
            if (klass.isNull()) return null;
            var n = readCStr(fn.class_get_name(klass));
            var ns = readCStr(fn.class_get_namespace(klass));
            return ns ? ns + "." + n : n;
        } catch (e) {
            return null;
        }
    }

    // Helper: read il2cpp array length
    function readArrayLength(arrPtr) {
        if (!arrPtr || arrPtr.isNull()) return -1;
        try {
            var lenOffset = ptrSize === 8 ? 24 : 12;
            return arrPtr.add(lenOffset).readS32();
        } catch (e) {
            return -1;
        }
    }

    // Helper: derive API short name from a task class name
    function taskToApiName(taskClassName) {
        return taskClassName.replace("Gallop.", "").replace(/Task$/, "");
    }

    // ── Step 1: Pre-scan Request/Response data classes ────────────────
    //
    // Each API has matching Gallop.*Request and Gallop.*Response classes
    // with actual data fields (story_id, choice_number, stat changes etc.)
    // We extract their field lists so we can read Response objects after
    // Deserialize returns them, and Request objects if we find them.

    console.log("[network] Scanning for Request/Response data classes...");

    var dataClassPtrs = Object.create(null); // className → classPtr

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        if (ns !== "Gallop") return;
        if (name.endsWith("Request") || name.endsWith("Response")) {
            dataClassPtrs[fullName] = classPtr;
        }
    });

    // Extract field info for each Request/Response class
    var dataClassInfoCache = Object.create(null); // className → classInfo

    function getDataClassInfo(className) {
        if (className in dataClassInfoCache) return dataClassInfoCache[className];
        var cp = dataClassPtrs[className];
        if (!cp) {
            dataClassInfoCache[className] = null;
            return null;
        }
        var info = extractClassInfoWithParents(cp, className);
        dataClassInfoCache[className] = info;
        return info;
    }

    // Cache for task class info extracted at runtime (keyed by class name)
    var taskClassInfoCache = Object.create(null);

    function getTaskClassInfo(objPtr, className) {
        if (className in taskClassInfoCache) return taskClassInfoCache[className];
        try {
            var klass = objPtr.readPointer();
            if (!klass || klass.isNull()) return null;
            var info = extractClassInfoWithParents(klass, className);
            taskClassInfoCache[className] = info;
            return info;
        } catch (e) {
            taskClassInfoCache[className] = null;
            return null;
        }
    }

    console.log(
        "[network] Found " + Object.keys(dataClassPtrs).length + " Request/Response data classes.",
    );

    // ── Step 2: Scan Task classes ─────────────────────────────────────

    var taskClasses = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        // Match Gallop.*Task classes (the API call wrappers)
        if (ns !== "Gallop") return;
        if (!name.endsWith("Task")) return;
        // Skip obvious non-API classes
        if (name.indexOf("UniTask") !== -1) return;
        if (name.indexOf("Coroutine") !== -1) return;
        taskClasses[fullName] = classPtr;
    });

    var taskCount = Object.keys(taskClasses).length;
    console.log("[network] Found " + taskCount + " Gallop.*Task classes.");

    // ── Step 3: Install hooks ─────────────────────────────────────────
    //
    // Because Send/Deserialize/OnError are inherited base-class methods,
    // hookMethod will only succeed for the FIRST task (dedup).
    // The callbacks must NOT rely on closure-captured task-specific vars —
    // they resolve everything dynamically via readClassName(self).

    var taskHooks = 0;
    var MAX_TASK_HOOKS = 600;

    for (var taskFqn in taskClasses) {
        if (taskHooks >= MAX_TASK_HOOKS) break;

        (function (fullName) {
            var classPtr = taskClasses[fullName];
            var info = extractClassInfo(classPtr, fullName);

            // Hook Send — fires when the game sends this API request
            if (info.methods["Send"]) {
                if (
                    hookMethod(info, "Send", -1, {
                        onEnter: function (args) {
                            var self = args[0];
                            var taskName = readClassName(self) || "UnknownTask";
                            var apiName = taskToApiName(taskName);

                            // Read postData byte[] at offset 16
                            var postDataSize = -1;
                            var postDataBuf = null;
                            try {
                                var arrPtr = self.add(16).readPointer();
                                if (arrPtr && !arrPtr.isNull()) {
                                    postDataSize = readArrayLength(arrPtr);
                                    if (postDataSize > 0 && postDataSize <= 1048576) {
                                        postDataBuf = readIl2cppByteArray(arrPtr, 262144);
                                        if (!postDataBuf) {
                                            console.log(
                                                "[network] WARN: readIl2cppByteArray returned null for " +
                                                    apiName +
                                                    " (len=" +
                                                    postDataSize +
                                                    ", arrPtr=" +
                                                    arrPtr +
                                                    ")",
                                            );
                                        }
                                    }
                                }
                            } catch (e) {
                                console.log(
                                    "[network] ERROR reading postData for " + apiName + ": " + e,
                                );
                            }

                            var record = {
                                event: "api_send",
                                task: taskName,
                                api: apiName,
                                postDataBytes: postDataSize,
                            };

                            send(
                                {
                                    type: "collect",
                                    domain: "network",
                                    data: record,
                                },
                                postDataBuf,
                            );
                        },
                    })
                ) {
                    taskHooks++;
                }
            }

            // Hook Deserialize — fires when the response is parsed.
            // retval is the deserialized Response object.
            // args[1] may be the raw response byte[] or a MessagePackReader.
            if (info.methods["Deserialize"]) {
                if (
                    hookMethod(info, "Deserialize", -1, {
                        onEnter: function (args) {
                            this._self = args[0];
                            this._taskName = readClassName(args[0]) || "UnknownTask";
                            this._apiName = taskToApiName(this._taskName);

                            // Try to capture raw response bytes from args[1]
                            // (byte[] parameter to Deserialize)
                            this._rawBuf = null;
                            try {
                                var rawArg = args[1];
                                if (rawArg && !rawArg.isNull()) {
                                    // Check if it looks like an il2cpp array
                                    var len = readArrayLength(rawArg);
                                    if (len > 0 && len < 1048576) {
                                        this._rawBuf = readIl2cppByteArray(rawArg, 262144);
                                    }
                                }
                            } catch (e) {}
                        },
                        onLeave: function (retval) {
                            var record = {
                                event: "api_response",
                                task: this._taskName,
                                api: this._apiName,
                            };

                            // ── Read Response object fields from retval ──
                            // Deserialize returns the typed Response object
                            // (e.g. SingleModeFreeCheckEventResponse).
                            // Look up its class info and read all primitive fields.
                            try {
                                if (retval && !retval.isNull()) {
                                    // Get the actual Response class name from retval's klass
                                    var retClassName = readClassName(retval);
                                    if (retClassName) {
                                        record.responseClass = retClassName;
                                        var respInfo = getDataClassInfo(retClassName);
                                        if (!respInfo) {
                                            // Fallback: extract fields on the fly via IL2CPP reflection
                                            try {
                                                var retKlass = retval.readPointer();
                                                if (!retKlass.isNull()) {
                                                    respInfo = extractClassInfoWithParents(
                                                        retKlass,
                                                        retClassName,
                                                    );
                                                }
                                            } catch (e) {}
                                        }
                                        if (respInfo && respInfo.fieldList.length > 0) {
                                            var fields = readObjectFields(
                                                retval,
                                                respInfo.fieldList,
                                            );
                                            if (fields) record.responseFields = fields;
                                        }
                                    }
                                }
                            } catch (e) {
                                console.log(
                                    "[network] WARN: failed reading retval for " +
                                        this._apiName +
                                        ": " +
                                        e,
                                );
                            }

                            // ── Also try reading task object fields after Deserialize ──
                            // Task classes end in "Task" not "Request"/"Response",
                            // so they're not in dataClassPtrs. Extract live (cached).
                            try {
                                if (this._self && !this._self.isNull()) {
                                    var taskInfo = getTaskClassInfo(this._self, this._taskName);
                                    if (taskInfo && taskInfo.fieldList.length > 0) {
                                        var tFields = readObjectFields(
                                            this._self,
                                            taskInfo.fieldList,
                                        );
                                        if (tFields) record.taskFields = tFields;
                                    }
                                }
                            } catch (e) {}

                            send(
                                {
                                    type: "collect",
                                    domain: "network",
                                    data: record,
                                },
                                this._rawBuf || null,
                            );
                        },
                    })
                ) {
                    taskHooks++;
                }
            }

            // Hook OnError
            if (info.methods["OnError"]) {
                if (
                    hookMethod(info, "OnError", -1, {
                        onEnter: function (args) {
                            var self = args[0];
                            var taskName = readClassName(self) || "UnknownTask";

                            send({
                                type: "collect",
                                domain: "network",
                                data: {
                                    event: "api_error",
                                    task: taskName,
                                    api: taskToApiName(taskName),
                                },
                            });
                        },
                    })
                ) {
                    taskHooks++;
                }
            }
        })(taskFqn);
    }

    hookCount += taskHooks;
    console.log("[network] " + taskHooks + " Gallop Task hooks installed.");

    // ── Summary ───────────────────────────────────────────────────────

    console.log("[network] Total: " + hookCount + " network hooks installed.");
    send({ type: "hook_status", module: "network", hookCount: hookCount });
})();
