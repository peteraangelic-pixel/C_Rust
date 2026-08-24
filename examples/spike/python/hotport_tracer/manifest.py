"""Budowa i zapis manifestu — format ZAMROŻONY: hotport.manifest/0.1.0.

Reguły semver dla manifestu:
* dodanie pola OPCJONALNEGO = minor (0.2.0),
* zmiana/-usunięcie istniejącego pola lub semantyki = major (1.0.0),
* konsumenci MUSZĄ ignorować nieznane pola.
"""

import datetime
import json

SCHEMA_VERSION = "hotport.manifest/0.1.0"


def _median(xs):
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def _fn_entry(st):
    durations_us = [d / 1000.0 for d in st.durations]
    return {
        "calls": st.calls,
        "self_ms": st.self_ns / 1e6,
        "median_us": _median(durations_us),
        "args": {
            slot: sorted(shapes)
            for slot, shapes in sorted(st.arg_shapes.items())
        },
        "ret": sorted(st.ret_shapes),
        "truthy_fraction": (st.truthy / st.calls) if st.calls else None,
        "raises": sorted(st.raises),
        "mutates_args": st.mutated,           # K4
        "ascii_fraction": (st.ascii_strs / st.total_strs) if st.total_strs else None,  # ADR-0005
        "replay": st.samples,                 # wejścia L1 dla differentialu
    }


def build_manifest(stats, target_module="?", command=None):
    """stats: {(module, qualname): _FnStats} → słownik manifestu."""
    functions = {}
    for (module, qualname), st in sorted(stats.items()):
        if st.calls == 0:
            continue  # nieobserwowane funkcje nie wchodzą do manifestu
        functions[qualname] = _fn_entry(st)
    return {
        "schema": SCHEMA_VERSION,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "target": {"module": target_module},
        "command": list(command) if command else None,
        "functions": functions,
    }


def write_manifest(manifest, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    return path
