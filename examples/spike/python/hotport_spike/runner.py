"""Silnik różnicowy L1/L2 (PLAN.md §4.2) + bramka (§4.3) + raport.

Prawda = oryginał Pythona (validators). Kandydat = backend rdzenia
(ref = specyfikacja, rust = ctypes). Rozbieżność ≠ błąd testu — to sygnał
do człowieka (Z5), ale bramka MUSI być czerwona.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import hotport_spike  # noqa: E402,F401 — efekt uboczny: ścieżka vendora na sys.path

import validators  # noqa: E402

from hotport_spike import ref_backend, rust_backend  # noqa: E402

_FN = {"slug": validators.slug, "uuid": validators.uuid, "ipv4": validators.ipv4}
_SUPPORTED_KWARGS = {"cidr", "strict", "host_bit"}
_UNREPLAYABLE = object()


def _decode(v):
    if isinstance(v, dict):
        if "$uuid" in v:
            import uuid as uuid_mod
            return uuid_mod.UUID(hex=v["$uuid"])
        return _UNREPLAYABLE  # {"$repr": ...} — nieodtwarzalna próbka
    return v


def cases_from_manifest(manifest):
    """Replay z manifestu tracera → przypadki differential (warstwa l1-trace).

    Pomijamy próbki z nieodtwarzalnymi argumentami oraz te, których kwargs
    wykraczają poza wspierany podzbiór (np. private≠None — poza MVP).
    """
    cases, skipped = [], {"unreplayable": 0, "unsupported-kwargs": 0}
    for name, entry in (manifest.get("functions") or {}).items():
        if name not in _FN:
            continue  # spike wspiera slug/uuid/ipv4
        for sample in entry.get("replay", []):
            args = [_decode(a) for a in sample.get("args", [])]
            kwargs_raw = sample.get("kwargs", {})
            kwargs = {}
            bad = any(a is _UNREPLAYABLE for a in args)
            for k, v in kwargs_raw.items():
                dv = _decode(v)
                if k not in _SUPPORTED_KWARGS:
                    if dv is not None and dv is not False and dv is not _UNREPLAYABLE:
                        bad = True  # np. private=True → poza zakresem rdzenia
                    continue
                if dv is _UNREPLAYABLE:
                    bad = True
                else:
                    kwargs[k] = dv
            if bad:
                skipped["unreplayable" if any(a is _UNREPLAYABLE for a in args) else "unsupported-kwargs"] += 1
                continue
            if len(args) != 1:
                skipped["unreplayable"] += 1
                continue
            cases.append({"fn": name, "value": args[0], "kwargs": kwargs, "origin": "l1-trace"})
    return cases, skipped


def py_outcome(case):
    """true/false/raise:ExcName — przez pełne API (dekorator włącznie)."""
    try:
        r = _FN[case["fn"]](case["value"], **case.get("kwargs", {}))
    except Exception as e:  # noqa: BLE001 — chcemy klasyfikować WSZYSTKIE
        return f"raise:{type(e).__name__}"
    return "true" if bool(r) else "false"


def core_outcome(backend, case):
    """true/false/routed — bez dekoratora, czysty predykat rdzenia."""
    try:
        r = backend.CORES[case["fn"]](case["value"], **case.get("kwargs", {}))
    except Exception as e:  # noqa: BLE001
        return f"error:{type(e).__name__}"
    return "routed" if r is None else ("true" if r else "false")


def compare(backend, cases):
    """Zwraca (statystyki, rozbieżności). routed nie liczy się do porównania
    rdzenia, ale ścieżka shimu i tak przechodzi parity w testach pytest."""
    stats = {}
    diffs = []
    for case in cases:
        fn = case["fn"]
        s = stats.setdefault(fn, {"total": 0, "compared": 0, "routed": 0, "mismatch": 0})
        s["total"] += 1
        py = py_outcome(case)
        core = core_outcome(backend, case)
        if core == "routed":
            s["routed"] += 1
            # routing musi być uzasadniony: nie-str albo nie-ASCII
            v = case["value"]
            if isinstance(v, str) and v.isascii() and not (case["fn"] == "ipv4" and case.get("kwargs", {}).get("private") is not None):
                diffs.append({**case, "py": py, "core": core, "reason": "NIEUZASADNIONY routing (ASCII str)"})
                s["mismatch"] += 1
            continue
        s["compared"] += 1
        if core != py:
            s["mismatch"] += 1
            diffs.append({**case, "py": py, "core": core})
    return stats, diffs


def gate(stats, diffs):
    ok = not diffs and all(s["mismatch"] == 0 for s in stats.values())
    return ok


def write_report(backend_name, stats, diffs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"# Raport differential — backend: {backend_name}",
        "",
        "| fn | przypadki | porównane | routed | rozbieżności |",
        "|---|---|---|---|---|",
    ]
    for fn, s in sorted(stats.items()):
        lines.append(f"| {fn} | {s['total']} | {s['compared']} | {s['routed']} | {s['mismatch']} |")
    verdict = "PASS ✅" if gate(stats, diffs) else "FAIL ❌"
    lines += ["", f"**Bramka: {verdict}**", ""]
    if diffs:
        lines.append("## Rozbieżności (max 20)")
        for d in diffs[:20]:
            kw = d.get("kwargs", {})
            reason = f" — {d['reason']}" if "reason" in d else ""
            lines.append(f"- `{d['fn']}({d['value']!r}, {kw})`: python={d['py']}, core={d['core']}{reason}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(path.replace(".md", ".json"), "w", encoding="utf-8") as f:
        json.dump({"backend": backend_name, "stats": stats,
                   "diffs": [{k: str(v) for k, v in d.items()} for d in diffs]}, f,
                  ensure_ascii=False, indent=1)
    return verdict


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["ref", "rust"], default="ref")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-fn", type=int, default=250)
    ap.add_argument("--manifest", default=None,
                    help="manifest tracera: replay z prawdziwych wywołań (warstwa l1-trace)")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    from hotport_spike import gen

    backend = {"ref": ref_backend, "rust": rust_backend}[args.backend]
    if args.backend == "rust" and not rust_backend.available():
        print(f"BLAD: {rust_backend.why_unavailable()}", file=sys.stderr)
        return 2
    cases = gen.all_cases(seed=args.seed, per_fn=args.per_fn)
    if args.manifest:
        import json as _json
        with open(args.manifest, encoding="utf-8") as f:
            manifest = _json.load(f)
        extra, skipped = cases_from_manifest(manifest)
        print(f"manifest: +{len(extra)} przypadkow l1-trace (pominiete: {skipped})")
        cases += extra
    stats, diffs = compare(backend, cases)
    verdict = gate(stats, diffs)
    report = args.report or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "report",
        f"differential-{args.backend}.md",
    )
    v = write_report(args.backend, stats, diffs, report)
    print(f"backend={args.backend} przypadki={len(cases)} verdict={v}")
    print(f"raport: {report}")
    for fn, s in sorted(stats.items()):
        print(f"  {fn:5} total={s['total']:4} compared={s['compared']:4} routed={s['routed']:3} mismatch={s['mismatch']}")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
