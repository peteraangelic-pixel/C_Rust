"""Testy tracera v1 (Faza 1) + ZAMKNIĘCIE PĘTLI:
ślad z prawdziwej suite → manifest → differential → bramka PASS."""

import json
import os
import sys
import types

import pytest

from hotport_tracer import Tracer, shape_of
from hotport_tracer.manifest import SCHEMA_VERSION, build_manifest, write_manifest


def _synth():
    m = types.ModuleType("synthmod")

    def repeat(s, n=2):
        return s * n

    def boom(x):
        raise ValueError("nope")

    def mutate(lst):
        lst.append(1)
        return len(lst)

    def plain(a, b=1, *, c=None):
        return a + b

    m.repeat, m.boom, m.mutate, m.plain = repeat, boom, mutate, plain
    return m


def test_ksztalty_typow():
    assert shape_of("x") == "str"
    assert shape_of(True) == "bool"
    assert shape_of(None) == "None"
    assert shape_of([1, "a"]) == "list[int|str]"
    assert shape_of({"k": 1}) == "dict[str->int]"
    import uuid as u
    assert shape_of(u.uuid4()) == "uuid.UUID"


def test_tracer_zbiera_statystyki_i_probki():
    m = _synth()
    t = Tracer(max_samples=10)
    t.wrap_module(m)
    assert m.repeat("ab") == "abab"
    m.repeat("ab")            # dedup: ta sama próbka
    m.repeat(b"z", 3)
    with pytest.raises(ValueError):
        m.boom(1)
    assert m.mutate([1, 2]) == 3
    assert m.plain(5) == 6
    man = t.manifest(target_module="synthmod")
    f = man["functions"]
    assert f["repeat"]["calls"] == 3
    assert "str" in f["repeat"]["args"]["s"]
    assert "bytes" in f["repeat"]["args"]["s"]
    assert f["repeat"]["replay"][0] == {"args": ["ab"], "kwargs": {}}
    assert len(f["repeat"]["replay"]) == 2  # dedup działa
    assert f["boom"]["raises"] == ["ValueError"]
    assert f["mutate"]["mutates_args"] is True      # K4
    assert f["repeat"]["mutates_args"] is False
    # sloty z WARTOŚCIAMI DOMYŚLNYMI nie są obserwowane (nie w args); niezerowe
    # wywołania trafiają do manifestu, zerowe nie:
    assert f["plain"]["args"] == {"a": ["int"]}
    assert set(f) == {"repeat", "boom", "mutate", "plain"}
    t.unwrap_all()
    assert m.repeat.__name__ == "repeat"
    assert not hasattr(m.repeat, "__wrapped__") or m.repeat.__wrapped__ is not None


def test_manifest_roundtrip_i_schema(tmp_path):
    m = _synth()
    t = Tracer()
    t.wrap_module(m, names=["plain"])
    m.plain(1)
    man = t.manifest(target_module="synthmod", command=["pytest", "x"])
    assert man["schema"] == SCHEMA_VERSION
    assert SCHEMA_VERSION.startswith("hotport.manifest/0.")
    p = write_manifest(man, tmp_path / "m.json")
    with open(p, encoding="utf-8") as f:
        assert json.load(f)["schema"] == SCHEMA_VERSION


# ------------------------------------------------ pętla zamknięta (integracja)

_VENDOR_TESTS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "targets", "validators", "tests",
                 "test_slug.py"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "targets", "validators", "tests",
                 "test_uuid.py"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "targets", "validators", "tests",
                 "test_ip_address.py"),
]


def test_slad_suite_vendora_zasila_differential():
    import validators
    from hotport_spike import ref_backend, runner

    t = Tracer()
    t.wrap_module(validators, names=["slug", "uuid", "ipv4"])
    rc = pytest.main(["-q", "-p", "no:cacheprovider", *_VENDOR_TESTS])
    t.unwrap_all()
    assert rc == 0, "suite vendora ma byc zielona pod rejestrowaniem"

    man = t.manifest(target_module="validators")
    for fn in ("slug", "uuid", "ipv4"):
        assert man["functions"][fn]["calls"] > 5, fn

    cases, skipped = runner.cases_from_manifest(man)
    assert len(cases) >= 40, f"za malo przypadkow replay: {len(cases)}"
    assert any(c["origin"] == "l1-trace" for c in cases)
    stats, diffs = runner.compare(ref_backend, cases)
    for d in diffs[:5]:
        print("DIFF:", d)
    assert not diffs, "rozbieznosci na PRAWDZIWYCH wejsciach z suite vendora"
    print("manifest stats:", {k: v["calls"] for k, v in man["functions"].items()})
    print("l1-trace cases:", len(cases), "skipped:", skipped)
