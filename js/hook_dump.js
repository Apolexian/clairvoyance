// hook_dump.js
// Data-driven field dumper. Receives class layouts from interesting.json
// (injected by Python at load time) and hooks key methods on the top-scored
// classes. When a method fires, reads all fields from `this` using known
// offsets and types, then sends the full snapshot as a collect event.
//
// This is the "actually capture game state" module.
// Loaded after il2cpp_helpers.js inside a collector IIFE.

(function () {
    "use strict";

    // Injected by Python at load time — array of {name, category, score, methods, fields}
    var DUMP_TARGETS = INJECTED_DUMP_TARGETS;

    console.log("[dump] Data-driven field dumper starting...");
    console.log("[dump] " + DUMP_TARGETS.length + " target classes to hook.");

    // Methods worth hooking — if a class has any of these, hook them.
    // These are the "something just happened" entry points.
    var HOOK_METHODS = [
        "Deserialize",
        "Serialize",
        "BeginView",
        "Begin",
        "StartView",
        "Activate",
        "LotActivate",
        "CheckTriggerAndActivate",
        "Send",
        "OnComplete",
        "OnSuccess",
        "SetResult",
        "ShowResult",
        "OnFinish",
        "BeginRace",
        "StartRace",
        "EndRace",
        "FinishRace",
        "OnClickDecide",
        "OnClickDecideButton",
        "SelectChoice",
        "Record",
        "ToRaceHorseData",
    ];

    var hookMethodSet = {};
    for (var i = 0; i < HOOK_METHODS.length; i++) {
        hookMethodSet[HOOK_METHODS[i].toLowerCase()] = true;
    }

    // Prefix patterns — any method whose lowercased name starts with one
    // of these is also hookable.  Catches versioned variants like
    // Deserialize_Ver20201027_OrNewer without listing every one.
    var HOOK_PREFIXES = ["deserialize_", "serialize_"];

    function isHookable(methodName) {
        var lower = methodName.toLowerCase();
        if (lower in hookMethodSet) return true;
        for (var pi = 0; pi < HOOK_PREFIXES.length; pi++) {
            if (lower.indexOf(HOOK_PREFIXES[pi]) === 0) return true;
        }
        return false;
    }

    // Methods that populate `this` — must read fields AFTER the call returns.
    // Record also writes into `this` (snapshots current state into the struct).
    // ToRaceHorseData converts data into the struct.
    var READ_ON_LEAVE = {
        deserialize: true,
        serialize: true,
        record: true,
        toracehorse: true, // prefix match below
    };

    function shouldReadOnLeave(methodName) {
        var lower = methodName.toLowerCase();
        if (lower in READ_ON_LEAVE) return true;
        // Any Deserialize_*, Serialize_* variant
        if (lower.indexOf("deserialize") === 0) return true;
        if (lower.indexOf("serialize") === 0) return true;
        if (lower.indexOf("torace") === 0) return true;
        return false;
    }

    // ── Type readers ──────────────────────────────────────────────────
    // Given a field type string and a pointer, read the value.

    function readField(objPtr, offset, typeName) {
        try {
            if (typeName === "System.Int32" || typeName === "int") {
                return objPtr.add(offset).readS32();
            }
            if (typeName === "System.UInt32" || typeName === "uint") {
                return objPtr.add(offset).readU32();
            }
            if (typeName === "System.Int64" || typeName === "long") {
                return objPtr.add(offset).readS64().toNumber();
            }
            if (typeName === "System.UInt64" || typeName === "ulong") {
                return objPtr.add(offset).readU64().toNumber();
            }
            if (typeName === "System.Single" || typeName === "float") {
                return objPtr.add(offset).readFloat();
            }
            if (typeName === "System.Double" || typeName === "double") {
                return objPtr.add(offset).readDouble();
            }
            if (typeName === "System.Boolean" || typeName === "bool") {
                return objPtr.add(offset).readU8() !== 0;
            }
            if (typeName === "System.Byte" || typeName === "byte") {
                return objPtr.add(offset).readU8();
            }
            if (typeName === "System.SByte" || typeName === "sbyte") {
                return objPtr.add(offset).readS8();
            }
            if (typeName === "System.Int16" || typeName === "short") {
                return objPtr.add(offset).readS16();
            }
            if (typeName === "System.UInt16" || typeName === "ushort") {
                return objPtr.add(offset).readU16();
            }
            if (typeName === "System.String" || typeName === "string") {
                var strPtr = objPtr.add(offset).readPointer();
                if (strPtr.isNull()) return null;
                return readIl2cppString(strPtr);
            }
            // For arrays, just report the length (reading elements would be recursive)
            if (typeName.endsWith("[]")) {
                var arrPtr = objPtr.add(offset).readPointer();
                if (arrPtr.isNull()) return null;
                // il2cpp array: length at offset 24 (64-bit) or 12 (32-bit)
                var lenOffset = ptrSize === 8 ? 24 : 12;
                var len = arrPtr.add(lenOffset).readS32();
                return { _array: true, length: len };
            }
            // Skip complex types we can't read (other objects, generics, etc.)
            return undefined;
        } catch (e) {
            return undefined;
        }
    }

    // ── Scan and hook ─────────────────────────────────────────────────

    // First pass: find all target classes by name
    var targetLookup = Object.create(null);
    for (var ti = 0; ti < DUMP_TARGETS.length; ti++) {
        targetLookup[DUMP_TARGETS[ti].name] = DUMP_TARGETS[ti];
    }

    var foundClasses = Object.create(null);

    console.log("[dump] Scanning for target classes...");

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        if (!(fullName in targetLookup)) return;
        foundClasses[fullName] = {
            classPtr: classPtr,
            target: targetLookup[fullName],
        };
    });

    var foundCount = Object.keys(foundClasses).length;
    console.log("[dump] Found " + foundCount + " of " + DUMP_TARGETS.length + " target classes.");

    // Second pass: extract method info and install hooks
    var hookCount = 0;

    for (var className in foundClasses) {
        (function (className) {
            var entry = foundClasses[className];
            var target = entry.target;
            var info = extractClassInfo(entry.classPtr, className);
            var category = target.category || "raw";
            var fields = target.fields || [];

            // Filter to readable fields (skip offset 0 which are usually static/constants)
            var readableFields = [];
            for (var fi = 0; fi < fields.length; fi++) {
                var f = fields[fi];
                if (f.offset > 0 && f.type) {
                    readableFields.push(f);
                }
            }

            // Helper: build the snapshot and send it
            function makeSnapshotSender(clsName, mName, cat, rFields) {
                return function (self) {
                    if (!self || self.isNull()) return;
                    var snapshot = Object.create(null);
                    for (var ri = 0; ri < rFields.length; ri++) {
                        var rf = rFields[ri];
                        var val = readField(self, rf.offset, rf.type);
                        if (val !== undefined) {
                            snapshot[rf.name] = val;
                        }
                    }
                    send({
                        type: "collect",
                        domain: cat,
                        data: {
                            event: "dump",
                            class: clsName,
                            method: mName,
                            fields: snapshot,
                        },
                    });
                };
            }

            // Find hookable methods on this class
            var methodNames = Object.keys(info.methods);
            for (var mi = 0; mi < methodNames.length; mi++) {
                (function (methodName) {
                    if (!isHookable(methodName)) return;

                    var doSnapshot = makeSnapshotSender(
                        className,
                        methodName,
                        category,
                        readableFields,
                    );

                    var useLeave = shouldReadOnLeave(methodName);
                    var cb;
                    if (useLeave) {
                        // Deserialize / Record / etc.: fields are populated
                        // during the call, so read them AFTER the method returns.
                        // Also try retval — some Deserialize methods return a
                        // new struct instead of writing to `this`.
                        cb = {
                            onEnter: function (args) {
                                this._self = args[0];
                            },
                            onLeave: function (retval) {
                                doSnapshot(this._self);
                                // If retval is a non-null pointer that differs
                                // from self, also snapshot it (struct returned
                                // by value is common for Deserialize).
                                try {
                                    if (
                                        !retval.isNull() &&
                                        retval.toString() !== this._self.toString()
                                    ) {
                                        doSnapshot(retval);
                                    }
                                } catch (e) {}
                            },
                        };
                    } else {
                        cb = {
                            onEnter: function (args) {
                                doSnapshot(args[0]);
                            },
                        };
                    }

                    if (hookMethod(info, methodName, -1, cb)) {
                        hookCount++;
                    }
                })(methodNames[mi]);
            }
        })(className);
    }

    console.log("[dump] " + hookCount + " dump hooks installed across " + foundCount + " classes.");
    send({ type: "hook_status", module: "dump", hookCount: hookCount });
})();
