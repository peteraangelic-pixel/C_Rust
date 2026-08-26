"""Testy translatora v0 (Faza 2): golden, podzbiór, differential na cieniu,
czułość (wstrzyknięty saturujący mnożnik) — metodyka fazy 0 rozszerzona
na kod GENEROWANY automatycznie."""

import os
import sys

import pytest

from hotport_trans import shadow_module_source, translate_module
from hotport_spike import gen, runner

_TESTS = os.path.dirname(os.path.abspath(__file__))
_TARGETS = os.path.normpath(os.path.join(_TESTS, "..", "..", "targets"))
_GENERATED = os.path.normpath(os.path.join(_TESTS, "..", "generated"))

_DEMO_NAMES = ("in_band", "grade", "sum_upto", "code_ok", "safe_mul")


@pytest.fixture(scope="module", autouse=True)
def _register_demo():
    if _TARGETS not in sys.path:
        sys.path.insert(0, _TARGETS)
    import demo_fns
    for n in _DEMO_NAMES:
        runner.register_python(n, getattr(demo_fns, n))
    yield


@pytest.fixture(scope="module")
def translation():
    with open(os.path.join(_TARGETS, "demo_fns.py"), encoding="utf-8") as f:
        return translate_module(f.read(), filename="demo_fns.py")


def _exec_shadow(src):
    ns = {}
    exec(compile(src, "shadow_generated.py", "exec"), ns)  # noqa: S102
    return ns


def _backend(ns):
    b = type("ShadowBackend", (), {})()
    b.CORES = {n: ns[n] for n in _DEMO_NAMES if n in ns}
    b.NAME = "shadow"
    return b


# ------------------------------------------------------------ golden

def test_wsystkie_funkcje_przetlumaczone(translation):
    assert sorted(t["name"] for t in translation["functions"]) == sorted(_DEMO_NAMES)
    assert translation["rejected"] == []


def test_golden_stabilny(translation):
    """Pliki w generated/ == świeża regeneracja (anti-drift; commitowane artefakty)."""
    for t in translation["functions"]:
        p = os.path.join(_GENERATED, f"{t['name']}.rs")
        assert os.path.exists(p), f"brak golden: {p} (uruchom: python -m hotport_trans)"
        with open(p, encoding="utf-8") as f:
            assert f.read() == t["rust"], f"golden rozjechany: {p}"
    with open(os.path.join(_GENERATED, "shadow_generated.py"), encoding="utf-8") as f:
        assert f.read() == shadow_module_source(translation["functions"])


def test_zlote_reguly_emisji(translation):
    """Reguły-krycia: wygenerowany Rust zawiera kluczowe konstrukcje semantyczne."""
    rs = {t["name"]: t["rust"] for t in translation["functions"]}
    assert "chars().count()" in rs["code_ok"], "len(str) musi być chars().count() (nie bajty!)"
    assert "starts_with" in rs["code_ok"], "startswith → starts_with (mapowanie nazw)"
    assert "checked_add" in rs["sum_upto"], "arytmetyka int z kontrolą K3"
    assert "checked_mul" in rs["safe_mul"]
    assert "90.0" in rs["grade"], "literał int w porównaniu float → koercja f64"
    assert "let mut total" in rs["sum_upto"] and "\n        total = " in rs["sum_upto"], (
        "ponowne przypisanie = przypisanie, nie let (bug v0 złapany!)",
    )


# ------------------------------------------------------------ podzbiór

def test_podzbior_v0_odrzuca_try_i_calkowite_dzielenie():
    src = (
        "def f(a: int) -> int:\n"
        "    try:\n"
        "        return a // 2\n"
        "    except Exception:\n"
        "        return 0\n"
    )
    res = translate_module(src)
    assert len(res["rejected"]) == 1
    assert "Try" in res["rejected"][0][1]


def test_podzbior_v0_odrzuca_truthiness():
    src = "def g(s: str) -> bool:\n    if s:\n        return True\n    return False\n"
    res = translate_module(src)
    assert res["rejected"] and "truthiness" in res["rejected"][0][1]


# ------------------------------------------------------------ differential

def test_differential_oracle_vs_cien(translation):
    ns = _exec_shadow(shadow_module_source(translation["functions"]))
    cases = gen.demo_cases(seed=99, per_fn=120)
    stats, diffs = runner.compare(_backend(ns), cases)
    for d in diffs[:5]:
        print("DIFF:", d)
    assert not diffs
    total = sum(s["compared"] for s in stats.values())
    assert total > 400
    # K3 żyje: część wywołań słusznie służy routingu (argument/wynik poza i64)
    assert stats["safe_mul"]["routed"] > 0
    assert stats["sum_upto"]["routed"] == 0  # małe n — nic nie routuje


def test_k3_granice_dokladnie(translation):
    """Punktowe sprawdzenie zachowania cienia na krawędziach i64."""
    ns = _exec_shadow(shadow_module_source(translation["functions"]))
    m = ns["safe_mul"]
    assert m(2, 3) == 6
    assert m(2**62, 2) is None          # wynik 2^63 > i64::MAX → routing
    assert m(2**63, 1) is None          # argument poza i64 → routing
    assert m(-(2**63), 1) == -(2**63)   # MIN mieści się (krawędź!)


# ------------------------------------------------------------ czułość

def test_bramka_lapie_saturujacy_mnoznik(translation):
    """Wstrzyknięty 'port zapomniał o checked_mul i nasycą' MUSI zostać wyłapany."""
    src = shadow_module_source(translation["functions"]).replace(
        "return _chk(a * b)",
        "return max(_I64_MIN, min(_I64_MAX, a * b))",
    )
    assert "max(_I64_MIN" in src, "string-surgery nie zadziałał"
    ns = _exec_shadow(src)
    cases = [c for c in gen.demo_cases(seed=7, per_fn=60) if c["fn"] == "safe_mul"]
    cases.append({"fn": "safe_mul", "args": [2**62, 2], "kwargs": {}, "origin": "injected-probe"})
    stats, diffs = runner.compare(_backend(ns), cases)
    flagged = [d for d in diffs if d.get("reason") is None]
    assert flagged, "saturujący mnożnik NIE został wyłapany"
    assert any(c["args"] == [2**62, 2] for c in flagged)
