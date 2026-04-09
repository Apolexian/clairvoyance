// discover_scan.js
// Broad discovery scan across all assemblies.
// Three match strategies so we don't miss things just because Cygames
// named them differently:
//
//   1. KEYWORD match  — class name contains one of the SCAN_KEYWORDS
//                       (same as before)
//
//   2. NAMESPACE dump — if SCAN_ALL_NAMESPACES is true, every class in
//                       the "Gallop" namespace (the game's main namespace)
//                       is included. Catches everything the game defines
//                       regardless of naming.
//
//   3. SIGNATURE match — even outside Gallop, if a class has methods or
//                        fields whose names match "interesting" patterns
//                        (Activate, Deserialize, proc, lottery, etc.) we
//                        include it. This catches helper/utility classes
//                        that do important work but have non-obvious names.
//
// Loaded after il2cpp_helpers.js.

(function () {
    "use strict";

    const SCAN_KEYWORDS = INJECTED_KEYWORDS; // replaced by Python
    const SCAN_ALL_NAMESPACES = INJECTED_SCAN_ALL; // bool — dump entire Gallop namespace
    const INTERESTING_SIGS = INJECTED_INTERESTING_SIGS; // method/field name substrings

    console.log("Clairvoyance discovery scan starting...");
    console.log("Keywords: " + SCAN_KEYWORDS.join(", "));
    console.log("Full namespace dump: " + SCAN_ALL_NAMESPACES);
    console.log("Signature patterns: " + INTERESTING_SIGS.join(", "));

    const results = {};
    let scanned = 0;
    let matchedByKeyword = 0;
    let matchedByNamespace = 0;
    let matchedBySignature = 0;

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        scanned++;

        // ── Strategy 1: keyword match on full class name ──────────
        var lower = fullName.toLowerCase();
        var byKeyword =
            SCAN_KEYWORDS.length > 0 &&
            SCAN_KEYWORDS.some(function (kw) {
                return lower.includes(kw);
            });

        // ── Strategy 2: full namespace dump (Gallop.*) ────────────
        var byNamespace = SCAN_ALL_NAMESPACES && ns === "Gallop";

        // ── Strategy 3: signature-based (peek at methods + fields) ─
        var bySignature = false;
        var peek = null;
        if (!byKeyword && !byNamespace && INTERESTING_SIGS.length > 0) {
            // Quick peek: extract methods + fields and check names
            peek = extractClassInfo(classPtr, fullName);
            var allNames = Object.keys(peek.methods).concat(
                peek.fieldList.map(function (f) {
                    return f.name;
                }),
            );
            var joined = allNames.join("|").toLowerCase();
            bySignature = INTERESTING_SIGS.some(function (sig) {
                return joined.includes(sig);
            });
        }

        if (!byKeyword && !byNamespace && !bySignature) return;

        if (byKeyword) matchedByKeyword++;
        else if (byNamespace) matchedByNamespace++;
        else matchedBySignature++;

        var info = peek || extractClassInfo(classPtr, fullName);

        var matchReason = byKeyword ? "keyword" : byNamespace ? "namespace" : "signature";

        results[fullName] = {
            matchReason: matchReason,
            methods: Object.keys(info.methods).map(function (mName) {
                return {
                    name: mName,
                    overloads: info.methods[mName].map(function (o) {
                        return {
                            paramCount: o.paramCount,
                            address: o.compiledAddr,
                        };
                    }),
                };
            }),
            fields: info.fieldList,
        };

        // Progress: log every 1000 matches instead of every single class
        var totalSoFar = matchedByKeyword + matchedByNamespace + matchedBySignature;
        if (totalSoFar % 1000 === 0) {
            console.log("  ... " + totalSoFar + " matches so far (" + scanned + " scanned)");
        }
    });

    // Also log periodic scan progress for really large assemblies
    var total = Object.keys(results).length;
    console.log("");
    console.log("Scan complete:");
    console.log("  Total classes scanned: " + scanned);
    console.log("  Matched by keyword:    " + matchedByKeyword);
    console.log("  Matched by namespace:  " + matchedByNamespace);
    console.log("  Matched by signature:  " + matchedBySignature);
    console.log("  Total matched:         " + total);

    send({
        type: "scan_result",
        classCount: total,
        totalScanned: scanned,
        matchedByKeyword: matchedByKeyword,
        matchedByNamespace: matchedByNamespace,
        matchedBySignature: matchedBySignature,
        classes: results,
    });
})();
