"""Testy KLASTRA v0.2 [REVIEW pkt 8-9]: tłumaczymy REGION, nie liście.

Łańcuch: admission -> in_band / is_score_valid -> grade. JEDNO przejście FFI
na cały region; wywołania wewnętrzne w Rust są darmowe.
"""

import os
import sys

import pytest

from hotport_spike import gen, runner, rust_backend
from hotport_trans import shadow_module_source, translate_cluster
from hotport_tracer.manifest import clusters_from_manifest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_TARGETS = os.path.normpath(os.path.join(_TESTS, "..", "..", "targets"))
_GENERATED = os.path.normpath(os.path.join(_TESTS, "..", "generated"))
_CORE = os.path.normpath(os.path.join(_TESTS, "..", "core"))

_MEMBERS = {"admission", "in_band", "is_score_valid", "grade"}


@pytest.fixture(scope="module", autouse=True)
def _register():
    if _TARGETS not in sys.path:
        sys.path.insert(0, _TARGETS)
    import demo_cluster

    runner.register_python("admission", demo_cluster.admission)
    yield


@pytest.fixture(scope="module")
def translation():
    with open(os.path.join(_TARGETS, "demo_cluster.py"), encoding="utf-8") as f:
        return translate_cluster(f.read(), "admission", filename="demo_cluster.py")


def _shadow_ns(translation):
    ns = {}
    exec(  # noqa: S102
        compile(shadow_module_source([]) + translation["shadow"], "shadow_cluster", "exec"),
        ns,
    )
    return ns


# ------------------------------------------------------------ golden

def test_golden_klastra(translation):
    with open(os.path.join(_GENERATED, "cluster_admission.rs"), encoding="utf-8") as f:
        assert f.read() == translation["rust"]
    with open(os.path.join(_GENERATED, "shadow_cluster_admission.py"), encoding="utf-8") as f:
        assert f.read() == shadow_module_source([]) + translation["shadow"]
    # cross-check: moduł Rust w core ZAWIERA dokładnie wygenerowany kod
    with open(os.path.join(_CORE, "src", "cluster.rs"), encoding="utf-8") as f:
        assert translation["rust"].strip() in f.read(), "core/src/cluster.rs rozjechany z generatorem"


def test_struktura_klastra(translation):
    assert translation["entry"] == "admission"
    assert set(translation["members"]) == _MEMBERS
    rust = translation["rust"]
    assert "pub fn admission" in rust
    assert "pub(crate) fn in_band" in rust  # wnętrza: crate-widoczne (ffi), nie publiczne
    assert "pub fn in_band" not in rust
    assert "?;" in rust  # wywołania wewnętrzne rozpakowują Option (jak cień przez _call)


# ------------------------------------------------------------ differential

def test_differential_oracle_vs_cien(translation):
    ns = _shadow_ns(translation)
    backend = type("ShadowCluster", (), {})()
    backend.CORES = {"admission": ns["admission"]}
    backend.NAME = "shadow-cluster"
    cases = gen.cluster_cases(seed=123, per_fn=150)
    stats, diffs = runner.compare(backend, cases)
    for d in diffs[:5]:
        print("DIFF:", d)
    assert not diffs
    assert stats["admission"]["compared"] > 100


@pytest.mark.skipif(not rust_backend.available(), reason=rust_backend.why_unavailable() or "brak .so")
def test_differential_rust_klaster():
    backend = type("RustCluster", (), {})()
    backend.CORES = {"admission": rust_backend.cluster_admission}
    backend.NAME = "rust-cluster"
    cases = gen.cluster_cases(seed=123, per_fn=150)
    stats, diffs = runner.compare(backend, cases)
    assert not diffs, f"klaster rust vs python: {len(diffs)} rozbieznosci"


# ------------------------------------------------------------ odkrywanie klastra

def test_odkrycie_klastra_ze_sladu():
    import demo_cluster
    from hotport_tracer import Tracer

    t = Tracer()
    t.wrap_module(demo_cluster)
    for p in (80.0, 50.0, 75.0):
        demo_cluster.admission(p, 0.0, 100.0)
    t.unwrap_all()
    man = t.manifest(target_module="demo_cluster")
    # call-graph: admission wołany z <root>, wnętrza z wnętrza klastra
    assert man["functions"]["admission"]["callers"] == {"<root>": 3}
    assert man["functions"]["grade"]["callers"] == {"is_score_valid": 3}
    cls = clusters_from_manifest(man)
    assert any(
        c["entry"] == "admission" and set(c["members"]) == _MEMBERS
        for c in cls
    ), cls
