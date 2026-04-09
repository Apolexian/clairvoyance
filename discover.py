# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "frida",
# ]
# ///

"""
Clairvoyance — Phase 1: Discovery
──────────────────────────────────
Scans all classes in GameAssembly for guide-relevant keywords and dumps
their full layouts (methods, fields, offsets) to discovery/class_dump.json.

With --trace, hooks key entry-point methods and logs call frequency
during gameplay so you know exactly what to target in Phase 2.

Usage:
  uv run discover.py                   # broad class scan → JSON dump
  uv run discover.py --trace           # live-trace during gameplay
  uv run discover.py --keywords extra  # add extra keywords to scan
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import traceback

from lib.attach import attach
from lib.session import save_discovery

# ── Paths ──────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JS_DIR = os.path.join(SCRIPT_DIR, "js")


# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("clairvoyance")

# ── CLI ────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Clairvoyance Discovery")
parser.add_argument(
    "--trace", action="store_true", help="Live-trace mode: hook methods and log call frequency"
)
parser.add_argument(
    "--all",
    action="store_true",
    help="Dump EVERY class in the Gallop namespace (no keyword filter)",
)
parser.add_argument(
    "--keywords", nargs="*", default=[], help="Extra keywords to include in the scan"
)
parser.add_argument("--timeout", type=int, default=600, help="How long to run trace mode (seconds)")
args = parser.parse_args()

# ── Default keywords ───────────────────────────────────────────────────────

# These cover the major domains guide writers care about.
SCAN_KEYWORDS = [
    # Skills
    "skill",
    "ability",
    # Events & story
    "event",
    "story",
    "choice",
    "scenario",
    # Race
    "race",
    "result",
    "jikkyo",
    # Training
    "training",
    "singlemode",
    # Status / parameters
    "status",
    "parameter",
    "factor",
    # Master data
    "masterdata",
    # Network / API
    "request",
    "response",
    "task",
    "formatter",
    "msgpack",
    "httpclien",
    "webrequest",
]

# For trace mode: which classes to look at
TRACE_CLASS_KEYWORDS = [
    "skillbase",
    "skilldetail",
    "skillmanager",
    "racemana",
    "raceresult",
    "singlemodeevent",
    "singlemodechar",
    "storyevent",
    "choicereward",
    "trainingview",
    "trainingcontrol",
    # Network / API
    "msgpack.formatter",
    "task",
    "httpclient",
    "webrequest",
]

# For trace mode: which method names are interesting (low-frequency event methods)
TRACE_METHOD_PATTERNS = [
    "activate",
    "begin",
    "start",
    "end",
    "finish",
    "result",
    "decide",
    "select",
    "choice",
    "proc",
    "lot",
    "trigger",
    "deserialize",
    "serialize",
    "onclick",
    "beginview",
]

# Signature patterns: method/field name substrings that indicate a class is
# interesting even if its *class name* doesn't match any keyword.
# This catches things like a class called "Gallop.ChanceCalculator" that has
# an "ActivateLot" field or a "Deserialize" method.
INTERESTING_SIGNATURES = [
    "activate",
    "proc",
    "lottery",
    "lot",
    "deserialize",
    "serialize",
    "beginrace",
    "finishrace",
    "raceresult",
    "eventchoice",
    "choicereward",
    "skillid",
    "abilitytype",
    "abilityvalue",
    "trainedchara",
    "charaid",
    "sendrequest",
    "onresponse",
]


def load_js(filename: str) -> str:
    """Read a JS file from the js/ directory."""
    path = os.path.join(JS_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_scan_script(keywords: list[str], scan_all: bool) -> str:
    """Build the full scan script: helpers + scan logic."""
    helpers = load_js("il2cpp_helpers.js")
    scan = load_js("discover_scan.js")
    # Inject all three config values
    scan = scan.replace("INJECTED_KEYWORDS", json.dumps(keywords))
    scan = scan.replace("INJECTED_SCAN_ALL", json.dumps(scan_all))
    scan = scan.replace("INJECTED_INTERESTING_SIGS", json.dumps(INTERESTING_SIGNATURES))
    return f"(function(){{\n{helpers}\n{scan}\n}})();"


def build_trace_script(class_keywords: list[str], method_patterns: list[str]) -> str:
    """Build the full trace script: helpers + trace logic."""
    helpers = load_js("il2cpp_helpers.js")
    trace = load_js("discover_trace.js")
    trace = trace.replace("INJECTED_CLASS_KEYWORDS", json.dumps(class_keywords))
    trace = trace.replace("INJECTED_METHOD_PATTERNS", json.dumps(method_patterns))
    return f"(function(){{\n{helpers}\n{trace}\n}})();"


# ── Message handlers ───────────────────────────────────────────────────────

scan_result: dict | None = None
trace_reports = []
is_ready = False
has_error = False


def on_message(message, data):
    global scan_result, is_ready, has_error

    msg_type = message.get("type")

    if msg_type == "send":
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return

        ptype = payload.get("type")

        if ptype == "error":
            has_error = True
            log.error("  [X] %s", payload.get("message", ""))

        elif ptype == "scan_result":
            scan_result = payload
            is_ready = True
            count = payload.get("classCount", 0)
            total = payload.get("totalScanned", 0)
            by_kw = payload.get("matchedByKeyword", 0)
            by_ns = payload.get("matchedByNamespace", 0)
            by_sig = payload.get("matchedBySignature", 0)
            log.info("")
            log.info("=" * 60)
            log.info("  SCAN COMPLETE")
            log.info("  %d classes matched out of %d total", count, total)
            log.info("    by keyword:   %d", by_kw)
            log.info("    by namespace: %d", by_ns)
            log.info("    by signature: %d", by_sig)
            log.info("=" * 60)

            # Print summary by domain
            classes = payload.get("classes", {})
            domains: dict[str, list[str]] = {}
            for cls_name in sorted(classes.keys()):
                # Rough domain categorisation
                lower = cls_name.lower()
                if "race" in lower:
                    domain = "race"
                elif "skill" in lower:
                    domain = "skill"
                elif "event" in lower or "story" in lower or "choice" in lower:
                    domain = "event"
                elif "training" in lower or "singlemode" in lower:
                    domain = "training"
                else:
                    domain = "other"
                domains.setdefault(domain, []).append(cls_name)

            for domain in ["skill", "race", "event", "training", "other"]:
                names = domains.get(domain, [])
                if not names:
                    continue
                log.info("")
                log.info("  ── %s (%d classes) ──", domain.upper(), len(names))
                for name in names[:20]:  # cap at 20 per domain in console
                    cls = classes[name]
                    n_methods = len(cls.get("methods", []))
                    n_fields = len(cls.get("fields", []))
                    log.info("    %s  [%d methods, %d fields]", name, n_methods, n_fields)
                if len(names) > 20:
                    log.info("    ... and %d more (see JSON dump)", len(names) - 20)

        elif ptype == "trace_ready":
            is_ready = True
            log.info("")
            log.info(
                "  Trace active: %d hooks on %d classes",
                payload.get("hookCount", 0),
                payload.get("tracedClasses", 0),
            )
            log.info("  Play the game — call frequency reports every 10s.")
            log.info("  Ctrl+C to stop and save report.")

        elif ptype == "trace_report":
            trace_reports.append(payload)
            methods = payload.get("methods", [])
            total = payload.get("totalCalls", 0)
            log.info("")
            log.info("  ── Trace report (%d total calls) ──", total)
            for entry in methods[:15]:
                log.info("    %6d  %s", entry["count"], entry["method"])
            if len(methods) > 15:
                log.info("    ... and %d more methods", len(methods) - 15)

    elif msg_type == "error":
        has_error = True
        log.error("  [X] JS Error: %s", message.get("description", ""))
        stack = message.get("stack")
        if stack:
            for line in str(stack).splitlines()[:10]:
                log.error("      %s", line)

    elif msg_type == "log":
        log.info("  [JS] %s", message.get("payload", ""))


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    log.info("=" * 60)
    log.info("  Clairvoyance — Discovery")
    log.info("=" * 60)
    log.info("")

    all_keywords = list(set(SCAN_KEYWORDS + args.keywords))

    if args.trace:
        log.info("  MODE: LIVE TRACE")
        log.info("  Hooking event-driven methods and logging call frequency.")
    elif args.all:
        log.info("  MODE: FULL NAMESPACE DUMP + KEYWORD + SIGNATURE")
        log.info("  Dumping EVERY class in Gallop namespace,")
        log.info("  plus keyword matches and signature-based discovery.")
        log.info("  Keywords: %s", ", ".join(sorted(all_keywords)))
        log.info("  Signatures: %s", ", ".join(sorted(INTERESTING_SIGNATURES)))
    else:
        log.info("  MODE: KEYWORD + SIGNATURE SCAN")
        log.info("  Keywords: %s", ", ".join(sorted(all_keywords)))
        log.info("  Signatures: %s", ", ".join(sorted(INTERESTING_SIGNATURES)))
        log.info("  (use --all to also dump entire Gallop namespace)")
    log.info("")

    session = attach()
    if session is None:
        sys.exit(1)

    try:
        if args.trace:
            src = build_trace_script(TRACE_CLASS_KEYWORDS, TRACE_METHOD_PATTERNS)
        else:
            src = build_scan_script(all_keywords, scan_all=args.all)

        script = session.create_script(src, runtime="v8")
        script.on("message", on_message)
        log.info("[*] Loading script...")
        script.load()
    except Exception as e:
        log.error("[X] Failed to load script: %s: %s", type(e).__name__, e)
        traceback.print_exc()
        sys.exit(1)

    # Wait for completion
    if args.trace:
        log.info("[*] Trace running for up to %ds. Ctrl+C to stop early.", args.timeout)
        try:
            for _ in range(args.timeout):
                time.sleep(1)
                if has_error:
                    break
        except KeyboardInterrupt:
            log.info("\n[*] Stopped by user.")

        # Save accumulated trace reports
        if trace_reports:
            # Merge all reports into a combined frequency table
            combined: dict[str, int] = {}
            for report in trace_reports:
                for entry in report.get("methods", []):
                    combined[entry["method"]] = combined.get(entry["method"], 0) + entry["count"]

            sorted_methods = sorted(combined.items(), key=lambda x: -x[1])
            trace_data = {
                "reportCount": len(trace_reports),
                "totalMethods": len(sorted_methods),
                "methods": [{"method": m, "count": c} for m, c in sorted_methods],
            }
            path = save_discovery("trace_report.json", trace_data)
            log.info("")
            log.info("  Trace report saved: %s", path)
            log.info("  Top methods:")
            for m, c in sorted_methods[:20]:
                log.info("    %8d  %s", c, m)
    else:
        # Scan mode: wait for result
        for _ in range(120):
            time.sleep(0.5)
            if is_ready or has_error:
                break

        if has_error:
            log.error("\n[X] Script failed.")
            sys.exit(1)

        if scan_result:
            path = save_discovery("class_dump.json", scan_result.get("classes", {}))
            log.info("")
            log.info("  Full class dump saved: %s", path)
        else:
            log.warning("  No scan result received.")

    log.info("")
    log.info("=" * 60)
    log.info("  Done.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
