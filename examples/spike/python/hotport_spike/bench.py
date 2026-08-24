"""Benchmark przed/po (Z7): oryginał vs rdzeń (ref/rust).

Uczciwość raportowa: 'ref' to implementacja PYTHONOWA specyfikacji rdzenia —
NIE jest deklaracją speedupa; pokazuje koszt samej logiki. Realne liczby
Rust pochodzą z backendu 'rust' (ctypes) i z CI (PyO3).
"""

import os
import statistics
import sys
import time

# katalog NAD pakietem (.../python) — tak samo jak conftest; wcześniej wstawiany
# był katalog pakietu i import hotport_spike działał tylko z PYTHONPATH=python
# (krok CI go nie ma — bug #7, złapany przez bramkę --backend rust w CI)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hotport_spike  # noqa: E402,F401 — efekt uboczny: ścieżka vendora na sys.path

import validators  # noqa: E402

from hotport_spike import gen, ref_backend, rust_backend  # noqa: E402


def _bench(fn, args_list, n):
    """Mediana ns/op z batchy; args_list zapętlamy."""
    batch = max(1, len(args_list))
    times = []
    for _ in range(7):
        t0 = time.perf_counter()
        for i in range(n):
            fn(args_list[i % batch])
        times.append((time.perf_counter() - t0) / n * 1e9)
    return statistics.median(times)


def workload(per_fn=400):
    """Mieszane workloady z generatora L2 (te same wejścia dla wszystkich)."""
    cases = [c for c in gen.generate(seed=7, per_fn=per_fn)
             if isinstance(c["value"], str) and not c.get("kwargs")]
    out = {}
    for fn in ("slug", "uuid", "ipv4"):
        out[fn] = [c["value"] for c in cases if c["fn"] == fn]
    return out


def main():
    n = 30_000
    w = workload()
    rows = []
    for fn, values in w.items():
        if not values:
            continue
        py = _bench(_wrap_validators(fn), values, n)
        ref = _bench(ref_backend.CORES[fn], values, n)
        row = {"fn": fn, "python": py, "ref": ref, "rust": None, "n_values": len(values)}
        if rust_backend.available():
            row["rust"] = _bench(rust_backend.CORES[fn], values, n)
        rows.append(row)
    lines = [
        "# Benchmark spike'a (median ns/op, n=%d wywołań, %s unikalnych wejść)" % (n, "…"),
        "",
        "| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        py, ref = r["python"], r["ref"]
        rust = f"{r['rust']:.0f}" if r["rust"] else "—"
        pr = f"{py / ref:.2f}x" if ref else "—"
        prr = f"{py / r['rust']:.2f}x" if r["rust"] else "—"
        lines.append(f"| {r['fn']} | {py:.0f} | {ref:.0f} | {rust} | {pr} | {prr} |")
    lines += [
        "",
        "Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),",
        "'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —",
        "to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).",
    ]
    report = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "report", "bench.md")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nraport: {report}")


def _wrap_validators(fn):
    f = {"slug": validators.slug, "uuid": validators.uuid, "ipv4": validators.ipv4}[fn]
    return f


if __name__ == "__main__":
    main()
