// il2cpp_helpers.js
// Shared il2cpp reflection engine for clairvoyance.
// Provides: gaMod, api, fn, readCStr, getFieldTypeName, extractClassInfo,
//           iterAssemblyClasses, hookMethod
//
// This file is loaded first by all Frida scripts via string concatenation.

"use strict";

const ptrSize = Process.pointerSize;

// ── Find GameAssembly ─────────────────────────────────────────────────

const GA_NAMES = [
    "GameAssembly.dll",
    "GameAssembly",
    "libil2cpp.so",
    "UnityFramework",
    "GameAssembly.dylib",
];

let gaMod = null;
for (const name of GA_NAMES) {
    try {
        gaMod = Process.getModuleByName(name);
        if (gaMod) break;
    } catch (e) {}
}
if (!gaMod) {
    send({ type: "error", message: "GameAssembly module not found" });
    throw new Error("GameAssembly not found");
}

// ── Resolve IL2CPP API ────────────────────────────────────────────────

function resolve(name) {
    try {
        if (typeof gaMod.findExportByName === "function")
            return gaMod.findExportByName(name) || null;
    } catch (e) {}
    try {
        return Module.findExportByName(gaMod.name, name) || null;
    } catch (e) {}
    return null;
}

const api = {};
const apiNames = [
    "il2cpp_domain_get",
    "il2cpp_domain_get_assemblies",
    "il2cpp_assembly_get_image",
    "il2cpp_image_get_class_count",
    "il2cpp_image_get_class",
    "il2cpp_image_get_name",
    "il2cpp_class_get_name",
    "il2cpp_class_get_namespace",
    "il2cpp_class_get_methods",
    "il2cpp_class_get_fields",
    "il2cpp_class_get_nested_types",
    "il2cpp_class_get_parent",
    "il2cpp_method_get_name",
    "il2cpp_method_get_param_count",
    "il2cpp_field_get_name",
    "il2cpp_field_get_offset",
    "il2cpp_field_get_type",
    "il2cpp_type_get_name",
    "il2cpp_class_from_name",
    "il2cpp_string_chars",
    "il2cpp_string_length",
];
for (const n of apiNames) api[n] = resolve(n);

const critical = [
    "il2cpp_domain_get",
    "il2cpp_domain_get_assemblies",
    "il2cpp_assembly_get_image",
    "il2cpp_image_get_class_count",
    "il2cpp_image_get_class",
    "il2cpp_class_get_name",
    "il2cpp_class_get_namespace",
    "il2cpp_class_get_methods",
    "il2cpp_method_get_name",
];
for (const n of critical) {
    if (!api[n]) {
        send({ type: "error", message: "Missing critical IL2CPP API: " + n });
        throw new Error("Missing: " + n);
    }
}

// ── NativeFunctions ───────────────────────────────────────────────────

const fn = {
    domain_get: new NativeFunction(api.il2cpp_domain_get, "pointer", []),
    domain_get_assemblies: new NativeFunction(api.il2cpp_domain_get_assemblies, "pointer", [
        "pointer",
        "pointer",
    ]),
    assembly_get_image: new NativeFunction(api.il2cpp_assembly_get_image, "pointer", ["pointer"]),
    image_get_class_count: new NativeFunction(api.il2cpp_image_get_class_count, "uint32", [
        "pointer",
    ]),
    image_get_class: new NativeFunction(api.il2cpp_image_get_class, "pointer", [
        "pointer",
        "uint32",
    ]),
    image_get_name: api.il2cpp_image_get_name
        ? new NativeFunction(api.il2cpp_image_get_name, "pointer", ["pointer"])
        : null,
    class_get_name: new NativeFunction(api.il2cpp_class_get_name, "pointer", ["pointer"]),
    class_get_namespace: new NativeFunction(api.il2cpp_class_get_namespace, "pointer", ["pointer"]),
    class_get_methods: new NativeFunction(api.il2cpp_class_get_methods, "pointer", [
        "pointer",
        "pointer",
    ]),
    class_get_fields: api.il2cpp_class_get_fields
        ? new NativeFunction(api.il2cpp_class_get_fields, "pointer", ["pointer", "pointer"])
        : null,
    class_get_nested_types: api.il2cpp_class_get_nested_types
        ? new NativeFunction(api.il2cpp_class_get_nested_types, "pointer", ["pointer", "pointer"])
        : null,
    class_get_parent: api.il2cpp_class_get_parent
        ? new NativeFunction(api.il2cpp_class_get_parent, "pointer", ["pointer"])
        : null,
    method_get_name: new NativeFunction(api.il2cpp_method_get_name, "pointer", ["pointer"]),
    method_get_param_count: api.il2cpp_method_get_param_count
        ? new NativeFunction(api.il2cpp_method_get_param_count, "uint32", ["pointer"])
        : null,
    field_get_name: api.il2cpp_field_get_name
        ? new NativeFunction(api.il2cpp_field_get_name, "pointer", ["pointer"])
        : null,
    field_get_offset: api.il2cpp_field_get_offset
        ? new NativeFunction(api.il2cpp_field_get_offset, "int32", ["pointer"])
        : null,
    field_get_type: api.il2cpp_field_get_type
        ? new NativeFunction(api.il2cpp_field_get_type, "pointer", ["pointer"])
        : null,
    type_get_name: api.il2cpp_type_get_name
        ? new NativeFunction(api.il2cpp_type_get_name, "pointer", ["pointer"])
        : null,
    string_chars: api.il2cpp_string_chars
        ? new NativeFunction(api.il2cpp_string_chars, "pointer", ["pointer"])
        : null,
    string_length: api.il2cpp_string_length
        ? new NativeFunction(api.il2cpp_string_length, "int32", ["pointer"])
        : null,
};

// ── Utility ───────────────────────────────────────────────────────────

function readCStr(p) {
    if (!p || p.isNull()) return "";
    try {
        return p.readUtf8String();
    } catch (e) {
        return "";
    }
}

function readIl2cppString(strPtr) {
    if (!strPtr || strPtr.isNull()) return null;
    if (!fn.string_chars || !fn.string_length) return null;
    try {
        const len = fn.string_length(strPtr);
        if (len <= 0 || len > 10000) return null;
        const chars = fn.string_chars(strPtr);
        if (chars.isNull()) return null;
        return chars.readUtf16String(len);
    } catch (e) {
        return null;
    }
}

function getFieldTypeName(fieldPtr) {
    if (!fn.field_get_type || !fn.type_get_name) return "?";
    try {
        const t = fn.field_get_type(fieldPtr);
        if (t.isNull()) return "?";
        return readCStr(fn.type_get_name(t));
    } catch (e) {
        return "?";
    }
}

// ── Class introspection ───────────────────────────────────────────────

function getNestedTypes(classPtr) {
    if (!fn.class_get_nested_types) return [];
    const nested = [];
    try {
        const iter = Memory.alloc(ptrSize);
        iter.writePointer(ptr(0));
        for (let i = 0; i < 100; i++) {
            const nt = fn.class_get_nested_types(classPtr, iter);
            if (nt.isNull()) break;
            nested.push(nt);
        }
    } catch (e) {}
    return nested;
}

function extractClassInfo(classPtr, fullName) {
    const classInfo = {
        fullName,
        methods: Object.create(null),
        fields: Object.create(null),
        fieldList: [],
    };

    // Methods
    const iter = Memory.alloc(ptrSize);
    iter.writePointer(ptr(0));
    for (let i = 0; i < 500; i++) {
        const method = fn.class_get_methods(classPtr, iter);
        if (method.isNull()) break;
        const mName = readCStr(fn.method_get_name(method));
        const paramCount = fn.method_get_param_count ? fn.method_get_param_count(method) : -1;
        let methodPtr = ptr(0);
        try {
            methodPtr = method.readPointer();
        } catch (e) {}
        classInfo.methods[mName] = classInfo.methods[mName] || [];
        classInfo.methods[mName].push({
            paramCount,
            methodInfoAddr: method.toString(),
            compiledAddr: methodPtr.toString(),
        });
    }

    // Fields
    if (fn.class_get_fields && fn.field_get_name) {
        const fIter = Memory.alloc(ptrSize);
        fIter.writePointer(ptr(0));
        for (let i = 0; i < 200; i++) {
            const field = fn.class_get_fields(classPtr, fIter);
            if (field.isNull()) break;
            const fName = readCStr(fn.field_get_name(field));
            const fOffset = fn.field_get_offset ? fn.field_get_offset(field) : -1;
            const fType = getFieldTypeName(field);
            classInfo.fields[fName] = { offset: fOffset, type: fType };
            classInfo.fieldList.push({ name: fName, offset: fOffset, type: fType });
        }
    }

    return classInfo;
}

// ── Assembly iteration ────────────────────────────────────────────────

const domain = fn.domain_get();
const _countBuf = Memory.alloc(4);
const _assembliesPtr = fn.domain_get_assemblies(domain, _countBuf);
const _asmCount = _countBuf.readU32();

/**
 * Iterate every class in every loaded assembly.
 * Calls `callback(classPtr, name, namespace)` for each.
 * Also recurses into nested types.
 */
function iterAssemblyClasses(callback) {
    function visit(classPtr, parentName) {
        const name = readCStr(fn.class_get_name(classPtr));
        const ns = readCStr(fn.class_get_namespace(classPtr));
        const fullName = parentName ? parentName + "." + name : ns ? ns + "." + name : name;

        callback(classPtr, fullName, ns, name);

        for (const nt of getNestedTypes(classPtr)) visit(nt, fullName);
    }

    for (let ai = 0; ai < _asmCount; ai++) {
        const asmPtr = _assembliesPtr.add(ai * ptrSize).readPointer();
        if (asmPtr.isNull()) continue;
        const image = fn.assembly_get_image(asmPtr);
        if (image.isNull()) continue;
        const classCount = fn.image_get_class_count(image);
        for (let ci = 0; ci < classCount; ci++) {
            let classPtr;
            try {
                classPtr = fn.image_get_class(image, ci);
            } catch (e) {
                continue;
            }
            if (!classPtr || classPtr.isNull()) continue;
            visit(classPtr, null);
        }
    }
}

// ── Hook helper ───────────────────────────────────────────────────────

// Track addresses we've already hooked to avoid duplicate attach errors
const _hookedAddrs = {};

/**
 * Hook a method on a class that has already been extracted via extractClassInfo.
 * @param {Object} classInfo - result of extractClassInfo()
 * @param {string} methodName
 * @param {number} paramCount - expected param count (-1 = any)
 * @param {Object} callback - Interceptor.attach callback { onEnter, onLeave }
 * @returns {boolean} true if hooked (or already hooked at that address)
 */
function hookMethod(classInfo, methodName, paramCount, callback) {
    if (!classInfo) return false;
    const overloads = classInfo.methods[methodName];
    if (!overloads || overloads.length === 0) return false;

    let match = overloads[0];
    if (paramCount >= 0) {
        const exact = overloads.find((o) => o.paramCount === paramCount);
        if (exact) match = exact;
    }

    const addr = ptr(match.compiledAddr);
    if (addr.isNull()) return false;

    const addrStr = addr.toString();
    if (addrStr in _hookedAddrs) {
        // Already hooked (inherited method shared across subclasses)
        return false;
    }

    try {
        Interceptor.attach(addr, callback);
        _hookedAddrs[addrStr] = classInfo.fullName + "." + methodName;
        return true;
    } catch (e) {
        console.log("[HOOK FAIL] " + classInfo.fullName + "." + methodName + ": " + e);
        return false;
    }
}
