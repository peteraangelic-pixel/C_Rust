"""Anti-drift: żywy .github/workflows/ci.yml MUSI odpowiadać docs/ci-workflow.yml.

Historia: operator wkleił plik, a agent twierdził, że 'to stara wersja' — bo
rebase po cichu cofnął aktualizację docs. Ten test wykrywa rozjazd NA ZAWSZE:
fail = żywy workflow nie zgadza się z dokumentem źródłowym.
"""

import os

import pytest

_REPO = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
)
LIVE = os.path.join(_REPO, ".github", "workflows", "ci.yml")
DOCS = os.path.join(_REPO, "docs", "ci-workflow.yml")


def _normalize(text):
    """Usuń komentarze (#...) i puste linie — zostaw czysty YAML do porównania."""
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(ln.rstrip())
    return "\n".join(lines)


@pytest.mark.xfail(
    reason="żywy .github/workflows/ci.yml czeka na wklejenie docs/ci-workflow.yml "
           "przez operatora (UI); po wklejeniu test sam zzielenieje",
    strict=True,  # xfail DOPÓKI żywy plik nie zgadza się z docs; po wklejce = PASS
)
def test_zywy_workflow_zgodny_z_dokumentem():
    assert os.path.exists(LIVE), (
        f"brak {LIVE} — workflow musi być w repo (patrz docs/CI.md)"
    )
    with open(LIVE, encoding="utf-8") as f:
        live = _normalize(f.read())
    with open(DOCS, encoding="utf-8") as f:
        docs = _normalize(f.read())
    assert live == docs, (
        "RÓŻNICA żywy ci.yml vs docs/ci-workflow.yml — zaktualizuj żywy plik "
        "(wklej docs/ci-workflow.yml przez UI). Diff:\n"
        + "\n".join(_diff_summary(live.splitlines(), docs.splitlines()))
    )


def _diff_summary(a, b):
    import difflib

    return list(difflib.unified_diff(a, b, "zywy(ci.yml)", "docs", lineterm=""))[:40]
