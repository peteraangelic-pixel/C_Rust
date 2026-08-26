"""Batch API (rayon) — parzystość z pythonem na dużym workloadzie.

Skip bez modułu hotport_rs (sandbox); w CI (po kroku kopiującym moduł PyO3)
test biega naprawdę.
"""

import pytest

from hotport_spike.bench_parallel import make_workload


def _module():
    try:
        import hotport_rs

        return hotport_rs
    except ImportError:
        return None


pytestmark = pytest.mark.skipif(_module() is None, reason="brak modułu PyO3 hotport_rs (CI)")


def test_ipv4_batch_parzystosc():
    import validators

    hotport_rs = _module()
    items = make_workload(n=10_000, seed=99)
    got = hotport_rs.ipv4_batch(items)
    want = [bool(validators.ipv4(s)) for s in items]
    assert got == want, f"rozjazdy: {sum(1 for a, b in zip(got, want) if a != b)}"


def test_ipv4_batch_pusta_lista():
    assert _module().ipv4_batch([]) == []
