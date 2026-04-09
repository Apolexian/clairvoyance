// discover_trace.js
// Live-trace mode: hooks a broad set of "interesting" methods and logs
// call frequency during gameplay so you know what to target.
// Loaded after il2cpp_helpers.js.

(function () {
    "use strict";

    // These are the classes & method-name patterns we want to trace.
    // We hook every method on matching classes whose name contains one of the
    // method patterns — this keeps it targeted enough to avoid lag.
    const TRACE_CLASS_KEYWORDS = INJECTED_CLASS_KEYWORDS; // replaced by Python
    const TRACE_METHOD_PATTERNS = INJECTED_METHOD_PATTERNS; // replaced by Python

    console.log("Clairvoyance live-trace starting...");
    console.log("Class keywords: " + TRACE_CLASS_KEYWORDS.join(", "));
    console.log("Method patterns: " + TRACE_METHOD_PATTERNS.join(", "));

    // Collect target classes first
    const targetClasses = {};

    iterAssemblyClasses(function (classPtr, fullName, ns, name) {
        const lower = fullName.toLowerCase();
        if (
            !TRACE_CLASS_KEYWORDS.some(function (kw) {
                return lower.includes(kw);
            })
        )
            return;
        targetClasses[fullName] = extractClassInfo(classPtr, fullName);
    });

    console.log("Found " + Object.keys(targetClasses).length + " target classes for tracing.");

    // Now hook methods matching the patterns
    const callCounts = {}; // "ClassName.MethodName" → count
    let hookCount = 0;
    const MAX_HOOKS = 500; // safety limit

    for (const [className, classInfo] of Object.entries(targetClasses)) {
        if (hookCount >= MAX_HOOKS) break;

        for (const [methodName, overloads] of Object.entries(classInfo.methods)) {
            if (hookCount >= MAX_HOOKS) break;

            const mLower = methodName.toLowerCase();
            const shouldTrace = TRACE_METHOD_PATTERNS.some(function (pat) {
                return mLower.includes(pat);
            });
            if (!shouldTrace) continue;

            // Only hook the first overload (lowest param count)
            const overload = overloads[0];
            const addr = ptr(overload.compiledAddr);
            if (addr.isNull()) continue;

            const key = className + "." + methodName;

            try {
                Interceptor.attach(addr, {
                    onEnter: function (_args) {
                        callCounts[key] = (callCounts[key] || 0) + 1;
                    },
                });
                hookCount++;
            } catch (e) {
                // skip unhookable methods
            }
        }
    }

    console.log("Installed " + hookCount + " trace hooks. Play the game — call counts accumulate.");

    send({
        type: "trace_ready",
        hookCount: hookCount,
        tracedClasses: Object.keys(targetClasses).length,
    });

    // Periodically report call counts
    const REPORT_INTERVAL_MS = 10000;

    setInterval(function () {
        // Sort by count descending, only send non-zero
        const entries = [];
        for (const [key, count] of Object.entries(callCounts)) {
            if (count > 0) entries.push({ method: key, count: count });
        }
        entries.sort(function (a, b) {
            return b.count - a.count;
        });

        if (entries.length > 0) {
            send({
                type: "trace_report",
                timestamp: Date.now(),
                methods: entries.slice(0, 100), // top 100
                totalCalls: entries.reduce(function (s, e) {
                    return s + e.count;
                }, 0),
            });
        }
    }, REPORT_INTERVAL_MS);
})();
