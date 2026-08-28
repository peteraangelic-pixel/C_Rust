"""Silnik różnicowy L1/L2 (PLAN.md §4.2) + bramka (§4.3) + raport.

Prawda = oryginał Pythona (validators). Kandydat = backend rdzenia
(ref = specyfikacja, rust = ctypes). Rozbieżność ≠ błąd testu — to sygnał
do człowieka (Z5), ale bramka MUSI być czerwona.
"""

import json
import os
import sys

# katalog NAD pakietem (.../python) — tak samo jak conftest; wcześniej wstawiany
# był katalog pakietu i import hotport_spike działał tylko z PYTHONPATH=python
# (krok CI go nie ma — bug #7, złapany przez bramkę --backend rust w CI)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hotport_spike  # noqa: E402,F401 — efekt uboczny: ścieżka vendora na sys.path

import validators  # noqa: E402

from hotport_spike import ref_backend, rust_backend  # noqa: E402

_FN = {"slug": validators.slug, "uuid": validators.uuid, "ipv4": validators.ipv4}
_SUPPORTED_KWARGS = {"cidr", "strict", "host_bit"}
_UNREPLAYABLE = object()
_EXTRA_PY = {}  # rejestr celów spoza validators (np. demo_fns dla translatora v0)


def register_python(name, fn):
    """Zarejestruj oryginał dla funkcji-celu spoza validators (translator v0)."""
    _EXTRA_PY[name] = fn


def python_fn(name):
    if name in _EXTRA_PY:
        return _EXTRA_PY[name]
    if name in _FN:
        return _FN[name]
    raise KeyError(f"nieznana funkcja celu: {name}")


def _label(r):
    """Normalizacja wyniku do porównywalnej etykiety (K1/K2: polityka ścisła)."""
    if isinstance(r, bool):
        return "true" if r else "false"
    if isinstance(r, float):
        return "float:" + repr(r)  # nan/-inf/0.0 konsekwentnie; ścisła polityka K2
    if isinstance(r, int):
        return "int:" + str(r)
    if isinstance(r, str):
        return "str:" + r
    if r is None:
        return "none"
    # obiekty z __bool__ (np. ValidationError w validators) → zgodnie z semantyką
    # predykatów (zachowanie identyczne jak w fazie 0/1)
    return "true" if bool(r) else "false"


def _case_args(case):
    if "args" in case:
        return list(case["args"])
    return [case["value"]]


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
    """true/false/int:N/float:X/str:S/raise:ExcName — przez pełne API oryginału."""
    try:
        r = python_fn(case["fn"])(*_case_args(case), **case.get("kwargs", {}))
    except Exception as e:  # noqa: BLE001 — klasyfikujemy WSZYSTKIE
        return f"raise:{type(e).__name__}"
    return _label(r)


def core_outcome(backend, case):
    """etykieta wyniku / routed / error:Exc — czysty predykat rdzenia (cień/backend)."""
    try:
        r = backend.CORES[case["fn"]](*_case_args(case), **case.get("kwargs", {}))
    except Exception as e:  # noqa: BLE001
        return f"error:{type(e).__name__}"
    return "routed" if r is None else _label(r)


_I64_MIN, _I64_MAX = -(2**63), 2**63 - 1


def compare(backend, cases):
    """Zwraca (statystyki, rozbieżności). routed nie liczy się do porównania
    rdzenia, ale MUSI być uzasadnione (Z5): nie-str/nie-ASCII (validators, ADR-0005)
    albo int poza i64 (cele translatora v0, kontrakt K3)."""
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
            args = _case_args(case)
            if fn in _EXTRA_PY:
                justified = any(
                    isinstance(a, int) and not isinstance(a, bool) and not (_I64_MIN <= a <= _I64_MAX)
                    for a in args
                ) or (py.startswith("int:") and not (_I64_MIN <= int(py[4:]) <= _I64_MAX))
                # (druga klauzula: WYNIK oryginału poza i64 → checked_* słusznie zwróciło None)
                # v0.1: // i % przez zero — python rzuca ZeroDivisionError, helper
                # zwraca None (routing); to ten sam kontrakt co overflow (K3)
                justified = justified or py.startswith("raise:ZeroDivisionError")
            else:
                v = args[0] if args else None
                justified = (
                    not isinstance(v, str)
                    or not v.isascii()
                    or (fn == "ipv4" and case.get("kwargs", {}).get("private") is not None)
                )
            if not justified:
                diffs.append({**case, "py": py, "core": core, "reason": "NIEUZASADNIONY routing"})
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
