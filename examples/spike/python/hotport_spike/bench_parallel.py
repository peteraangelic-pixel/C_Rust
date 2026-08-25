"""Benchmark RÓWNOLEGŁY [rayon]: batch API vs najlepsze starania Pythona.

Pytanie badawcze (operator): o ile więcej daje Rust+rayon na wielu rdzeniach
niż pythonowe rozwiązania jednowątkowe/wieloprocesowe?

Uczciwość porównania:
* python #1: zwykła list-comp (GIL — 1 rdzeń; tak wygląda 99% kodu),
* python #2: ProcessPoolExecutor z tuningiem chunksize (realny wielordzeniowy
  python; koszt spawn+pickle liczony w czas — tak działa w praktyce),
* rust: hotport_rs.ipv4_batch (JEDNO przejście FFI na listę; rayon; GIL
  zwolniony przez allow_threads) — wymaga modułu PyO3 (CI).
"""

import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hotport_spike  # noqa: E402,F401 — ścieżka vendora

import validators  # noqa: E402


def _py_ipv4(s):
    return bool(validators.ipv4(s))


def make_workload(n=100_000, seed=2026):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        if rng.random() < 0.7:  # ważone: 70% poprawnych
            out.append(".".join(str(rng.randint(0, 255)) for _ in range(4)))
        else:
            out.append(f"{rng.randint(256, 999)}.1.1.{rng.randint(0, 99)}")
    return out


def _median_ns(fn, repeat=5):
    ts = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def main():
    items = make_workload()
    n = len(items)

    t_listcomp = _median_ns(lambda: [_py_ipv4(s) for s in items])
    print(f"elementów: {n}")

    # python wieloprocesowy (fork, dziedziczy moduły; chunksize dobrany)
    try:
        from concurrent.futures import ProcessPoolExecutor
        import multiprocessing as mp

        procs = min(8, mp.cpu_count())
        chunk = max(1, n // (procs * 8))
        with ProcessPoolExecutor(max_workers=procs) as ex:
            _ = list(ex.map(_py_ipv4, items[:1000], chunksize=chunk))  # rozgrzewka
        t_pool = _median_ns(
            lambda: _run_pool(items, procs, chunk),
        )
    except Exception as e:  # noqa: BLE001
        print("ProcessPool niedostępny:", e)
        t_pool = None

    t_rust = None
    try:
        import hotport_rs

        hotport_rs.ipv4_batch(items[:1000])  # rozgrzewka
        t_rust = _median_ns(lambda: hotport_rs.ipv4_batch(items))
    except ImportError:
        print("hotport_rs (PyO3) niedostępny — uruchom w CI (workflow: docs/ci-workflow.yml)")

    lines = [
        "# Benchmark równoległy: ipv4 × %d elementów (median, 5 powtórzeń)" % n,
        "",
        "| wariant | czas [ms] | ns/element | vs list-comp | vs ProcessPool |",
        "|---|---|---|---|---|",
    ]
    base = t_listcomp
    rows = [("python list-comp (GIL, 1 rdzeń)", t_listcomp)]
    if t_pool is not None:
        rows.append((f"python ProcessPool×{procs}", t_pool))
    if t_rust is not None:
        rows.append(("rust ipv4_batch (rayon, GIL zwolniony)", t_rust))
    for name, t in rows:
        vs1 = base / t
        vs2 = (t_pool / t) if t_pool else None
        lines.append(
            "| %s | %.1f | %.0f | %.2fx | %s |"
            % (name, t * 1e3, t / n * 1e9, vs1, ("%.2fx" % vs2) if vs2 else "—")
        )
    print("\n".join(lines))
    report = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "report", "bench-parallel.md"
    )
    os.makedirs(os.path.dirname(report), exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("raport:", report)


def _run_pool(items, procs, chunk):
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(max_workers=procs) as ex:
        return list(ex.map(_py_ipv4, items, chunksize=chunk))


if __name__ == "__main__":
    main()
