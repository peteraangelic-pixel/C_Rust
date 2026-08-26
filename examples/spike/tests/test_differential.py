"""Testy differential spike'a fazy 0 (PLAN.md §4.2/4.3).

Grupy:
1. python vs ref (specyfikacja rdzenia) na L1+L2 — GŁÓWNA asercja fazy 0,
2. python vs rust (ctypes) — pomijane bez .so (w CI: budowane i wykonywane),
3. wstrzyknięte bugi MUSZĄ zostać wyłapane (czułość bramki),
4. parzystość API shimu (repr ValidationError, wycieki wyjątków, tryby),
5. kanarek 'both' — CanaryMismatch na żywo.
"""

import uuid as uuid_mod

import pytest
import validators

import hotport_spike
from hotport_spike import gen, ref_backend, runner, rust_backend


@pytest.fixture(autouse=True)
def _restore_mode():
    prev = hotport_spike._MODE
    yield
    hotport_spike._MODE = prev


# ---------------------------------------------------- 1. differential ref

def test_differential_python_vs_ref():
    cases = gen.all_cases(seed=42, per_fn=250)
    stats, diffs = runner.compare(ref_backend, cases)
    print(stats)
    for d in diffs[:10]:
        print("DIFF:", d)
    total = sum(s["compared"] for s in stats.values())
    assert total > 1000, f"za malo porownanych przypadkow: {total}"
    assert not diffs, f"rozbieznosci ref vs python: {len(diffs)}"


# ---------------------------------------------------- 2. differential rust

@pytest.mark.skipif(not rust_backend.available(), reason=rust_backend.why_unavailable() or "brak .so")
def test_differential_python_vs_rust():
    cases = gen.all_cases(seed=42, per_fn=250)
    stats, diffs = runner.compare(rust_backend, cases)
    assert not diffs, f"rozbieznosci rust vs python: {len(diffs)}"


def test_rust_backend_routing_nie_stringow_bez_so(monkeypatch):
    """Regresja buga #6 (CI, prawdziwe .so): nie-stringi musza dawac None
    (routing), nie False. Stub FFI => lapalne takze bez kompilacji Rusta."""
    import uuid as uuid_mod

    from hotport_spike import rust_backend

    class _FakeFn:
        def __init__(self, ret):
            self.ret = ret

        def __call__(self, data, _len, *_flags):
            assert isinstance(data, bytes), "FFI dostaje wylacznie bytes"
            return self.ret

    class _FakeLib:
        hotport_slug_is_valid = _FakeFn(1)
        hotport_uuid_is_valid = _FakeFn(1)
        hotport_ipv4_is_valid = _FakeFn(1)

    monkeypatch.setattr(rust_backend, "_lib", _FakeLib())
    monkeypatch.setattr(rust_backend, "_load_error", None)

    # nie-stringi -> None = routing do oryginahu (Z5); wczesniej bylo bool(None)=False!
    assert rust_backend.uuid_core(uuid_mod.uuid4()) is None
    assert rust_backend.uuid_core(123) is None  # oryginal: AttributeError wycieka
    assert rust_backend.slug_core(None) is None
    assert rust_backend.ipv4_core(None) is None
    # string ASCII -> wynik FFI wprost (1 -> True)
    assert rust_backend.uuid_core("cokolwiek") is True
    assert rust_backend.ipv4_core("1.1.1.1") is True
    # -1 z FFI = poza kontraktem rdzenia -> None
    _FakeLib.hotport_uuid_is_valid = _FakeFn(-1)
    assert rust_backend.uuid_core("x") is None


# ---------------------------------------------------- 3. czulosc bramki

class _Backend:
    def __init__(self, cores, name):
        self.CORES, self.NAME = cores, name


def _buggy_slug_leading_hyphen(value):
    """Przyjmuje wiodowy '-' (poprawnie: invalid)."""
    if not isinstance(value, str):
        return None
    return ref_backend.slug_core(value[1:]) if value.startswith("-") else ref_backend.slug_core(value)


def _buggy_uuid_no_hyphen_strip(value):
    """Port pominął krok replace('-','') → myśli, że 36 znaków ≠ 32 → invalid."""
    if not isinstance(value, str):
        return None
    if "-" in value:
        return False  # 'nie zmieści się' w 32 znakach
    return ref_backend.uuid_core(value)


def _buggy_uuid_reject_underscore(value):
    """Odrzuca '_' (poprawnie: PEP 515 je akceptuje)."""
    r = ref_backend.uuid_core(value)
    if r is True and isinstance(value, str) and "_" in value:
        return False
    return r


def _buggy_ipv4_leading_zeros(value, cidr=True, strict=False, host_bit=True):
    """Przyjmuje wiodowe zera w oktetach (poprawnie: invalid od 3.9.5)."""
    if not isinstance(value, str) or not value.isascii():
        return None
    import re as _re
    if not _re.fullmatch(r"(?:\d+\.){3}\d+(?:/\S+)?", value or ""):
        return ref_backend.ipv4_core(value, cidr, strict, host_bit)
    # dla oktetow z zerami wiodacymi: zdejmij zeroes i spytaj rdzen
    parts = (value.split("/", 1)[0]).split(".")
    if all(p.isdigit() and (len(p) == 1 or not p.startswith("0")) for p in parts):
        return ref_backend.ipv4_core(value, cidr, strict, host_bit)
    stripped = ".".join(str(int(p)) for p in parts) + (
        "/" + value.split("/", 1)[1] if "/" in value else ""
    )
    return ref_backend.ipv4_core(stripped, cidr, strict, host_bit)


def _buggy_ipv4_reject_prefix_zeros(value, cidr=True, strict=False, host_bit=True):
    """Odrzuca wiodowe zera w PREFIKSIE (poprawnie: '/024' jest VALID)."""
    r = ref_backend.ipv4_core(value, cidr, strict, host_bit)
    if r is True and isinstance(value, str) and "/" in value:
        mask = value.split("/", 1)[1]
        if mask.isdigit() and len(mask) > 1 and mask.startswith("0"):
            return False
    return r


@pytest.mark.parametrize(
    "backend,probe,expected_py",
    [
        (_Backend({"slug": _buggy_slug_leading_hyphen}, "buggy-slug"), "-abc", "false"),
        (_Backend({"uuid": _buggy_uuid_no_hyphen_strip}, "buggy-uuid-nohyphen"), "2bc1c94f-0deb-43e9-92a1-4775189ec9f8", "true"),
        (_Backend({"uuid": _buggy_uuid_reject_underscore}, "buggy-uuid-us"), "2bc1c94f_0deb43e992a14775189ec9f", "true"),
        (_Backend({"ipv4": _buggy_ipv4_leading_zeros}, "buggy-ipv4-zeros"), "0127.0.0.1", "false"),
        (_Backend({"ipv4": _buggy_ipv4_reject_prefix_zeros}, "buggy-ipv4-prefix"), "1.1.1.1/024", "true"),
    ],
)
def test_bramka_lapie_wstrzykniete_bugi(backend, probe, expected_py):
    # probe dolaczamy JAWNIE do zbioru — test ma byc deterministyczny,
    # niezaleznie od losowosci generatora L2
    cases = [c for c in gen.all_cases(seed=42, per_fn=100) if c["fn"] in backend.CORES]
    fn = next(iter(backend.CORES))
    probe_case = {"fn": fn, "value": probe, "kwargs": {}, "origin": "injected-probe"}
    cases.append(probe_case)
    stats, diffs = runner.compare(backend, cases)
    flagged = [d for d in diffs if d.get("reason") is None]
    assert flagged, f"bramka NIE zlapala buga {backend.NAME}"
    assert any(d["value"] == probe for d in flagged), f"bug {backend.NAME}: nie oflagowal {probe!r}"
    assert runner.py_outcome(probe_case) == expected_py


# ---------------------------------------------------- 4. parzystosc API

MODES = ["python", "rust", "both"]


@pytest.mark.parametrize("mode", MODES)
def test_shim_parzystosc_wynikow(mode):
    hotport_spike.set_mode(mode)
    shim = {"slug": hotport_spike.slug, "uuid": hotport_spike.uuid, "ipv4": hotport_spike.ipv4}
    for case in gen.all_cases(seed=7, per_fn=40):
        fn = case["fn"]
        kw = dict(case.get("kwargs", {}))
        out_orig = runner.py_outcome(case)
        try:
            r = shim[fn](case["value"], **kw)
            out_shim = "true" if bool(r) else "false"
        except Exception as e:  # noqa: BLE001
            out_shim = f"raise:{type(e).__name__}"
        assert out_shim == out_orig, (
            f"mode={mode} {fn}({case['value']!r}, {kw}): shim={out_shim} vs orig={out_orig}"
        )


def test_shim_repr_validation_error_identyczny():
    for v in ["my.slug", "abc"]:
        assert repr(hotport_spike.slug(v)) == repr(validators.slug(v)), v
    assert repr(hotport_spike.ipv4("900.1.1.1")) == repr(validators.ipv4("900.1.1.1"))


def test_shim_wycieki_wyjatkow_identyczne():
    # oryginał: AttributeError (int nie ma .replace) wycieka przez dekorator
    with pytest.raises(AttributeError):
        validators.uuid(123)
    with pytest.raises(AttributeError):
        hotport_spike.uuid(123)
    # falsy strzeżone:
    assert not bool(validators.uuid(None)) and not bool(hotport_spike.uuid(None))
    assert not bool(validators.slug(None)) and not bool(hotport_spike.slug(None))
    assert not bool(validators.ipv4(None)) and not bool(hotport_spike.ipv4(None))
    # UUID object przez routing:
    assert bool(hotport_spike.uuid(uuid_mod.uuid4()))
    # private kwarg — routing do oryginału:
    assert bool(hotport_spike.ipv4("10.0.0.1", private=True))
    assert not bool(hotport_spike.ipv4("8.8.8.8", private=True))
    assert bool(validators.ipv4("8.8.8.8", private=False))


def test_raise_validation_error_env_parzystosc(monkeypatch):
    monkeypatch.setenv("RAISE_VALIDATION_ERROR", "True")
    with pytest.raises(validators.ValidationError):
        validators.slug("x.x")
    with pytest.raises(validators.ValidationError):
        hotport_spike.slug("x.x")


# ---------------------------------------------------- 5. kanarek 'both'

def test_canary_both_lapie_rozjazd_na_zywo(monkeypatch):
    hotport_spike.set_mode("both")
    monkeypatch.setattr(hotport_spike, "active_backend", lambda: _Backend({"slug": _buggy_slug_leading_hyphen}, "buggy"))
    with pytest.raises(hotport_spike.CanaryMismatch):
        hotport_spike.slug("-abc")
    # a poprawny backend przechodzi:
    monkeypatch.setattr(hotport_spike, "active_backend", lambda: ref_backend)
    assert hotport_spike.slug("dobre-123") is True
    assert not bool(hotport_spike.slug("zle.slug"))
