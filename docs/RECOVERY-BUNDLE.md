# RECOVERY-BUNDLE — paczka awaryjna dla nowej sesji (v1, 2026-08-27)

> JEDEN plik zawiera całą pracę poprzedniej sesji, której nie udało się
> wypchnąć (push odcięty przy zamknięciu sesji). AGENT NOWEJ SESJI:
> 1) przeczytaj docs/HANDOFF.md (jeśli jest — jest też niżej),
> 2) dla każdej sekcji "### PLIK:" poniżej zapisz treść do podanej ścieżki
>    (nadpisując istniejącą wersję), sekcje "### EDYCJA:" zastosuj ręcznie,
> 3) usuń ten plik z repo po rozpakowaniu, zcommituj normalnie,
> 4) regeneruj goldens: cd examples/spike && PYTHONPATH=python:../targets
>    python -m hotport_trans ../targets/demo_fns.py --out generated
>    (plus --entry admission dla demo_cluster) — potem pytest.
> Jeśli workspace odziedziczył oryginalne pliki —.bundle jest nadmiarowy
> (usuń go po weryfikacji diffów).

### PLIK: `docs/HANDOFF.md`  (briefing poprzedniej sesji)
```markdown
# HANDOFF — briefing dla nowej sesji (przeczytaj jako PIERWSZY)

> Kontekst: ten plik pisze agent sesji kończącej się 2026-08-25 dla agenta
> sesji następnej (projekt **hotport**, repo `peteraangelic-pixel/C_Rust`,
> branch `arena/01a03364-c-rust`). Po tej lekturze: PLAN.md (plan+postępy)
> i REPORT.md (kronika z liczbami). Operator wklei Ci osobny krótki prompt
> startowy — ten dokument to rozwinięcie techniczne.

## 1. Stan repozytorium (krytyczne!)

* **GitHub (pewne)**: cała praca do commitu `e106caa` — fazy 0–2.1: plan,
  spike validators (13 złotych reguł), tracer (manifest 0.2.0 z call-graph),
  translator v0.2 z KLASTRAMI, zielone CI z bot-commitami raportów,
  pomiar „region vs liście". Repo jest PUBLICZNE (API czytane bez tokena).
* **Lokalnie (możliwe w Twoim workspace, zależnie od snapshotu)**: 3–4
  commity niewypchnięte (sesja zgasła na pushu): przywrócony **rayon-v2**
  (moduł PyO3 `hotport_rs` z `ipv4_batch`, bench_parallel, test_parallel),
  **translator v0.1** (`//`, `%`, neg z semantyką pythona: helpery
  `__floordiv`/`__pymod`/`__neg`), **ADR-0006** (Unicode dla slugify),
  **test_workflow_drift** (żywy ci.yml vs docs — xfail do wklejki operatora).
  Szukaj znaczników: `rayon` w `examples/spike/pyo3/Cargo.toml`,
  `__floordiv` w translatorze, `docs/decisions/ADR-0006*`.
* **Procedura startowa**: `git fetch origin`; jeśli HEAD lokalne zawiera
  commity spoza origin → **kwarantanna najpierw** (`git add -A && git commit`),
  potem `git rebase origin/arena/01a03364-c-rust`, konflikty: pliki
  `examples/spike/report/*` → wersja zdalna (bot), cała reszta → **moje**
  (uwaga: w rebase `--theirs` = przybywające/moje zmiany!). Potem push.

* **NOWA SESJA = NOWA GAŁĄŹ**: pracujesz na branchu wyznaczonym przez
  platformę (może mieć INNĄ nazwę niż `arena/01a03364-c-rust`). Punktem
  startowym jest **main**, który zawiera całą pracę poprzedniej sesji
  (PR scalony przy zamknięciu + merge operatora). Starego brancha
  (`arena/01a03364-c-rust`) nie ruszaj — historia bezpieczna, archiwalna.
  Jeśli Twoje workspace odziedziczyło nieprzepchnięte commity poprzedniej
  sesji — wypchnij je na SWÓJ branch sesyjny (nie na stary).

## 1.5 Incydent przedstartowy: przypadkowy merge operatora (2026-08-27)

Operator przypadkiem scalił coś na GitHubie (prawdopodobnie main→branch przez
PR „sync", ew. ponowne scalenie PR branch→main). **Merge nie usuwa historii**
— najwyżej dodał commit scalający na branchu. Twoje zadania:
1. `git fetch origin` → `git log --graph --oneline origin/main origin/arena/01a03364-c-rust -15`
   — zidentyfikuj commit(y) „Merge pull request #N" i kierunek.
2. Scenariusz A (main→branch): nieszkodliwy sync — po prostu zrebasuj lokalne
   commity kwarantanny na nowy tip brancha; NIC nie cofaj.
3. Scenariusz B (branch→main, duplikat): nic nie rób — main zawiera już
   wszystko dobre; kontynuuj na branchu per procedura.
4. Tylko jeśli merge wywołał konflikty/konfliktowe pliki raportów: przy rebasu
   `examples/spike/report/*` bierz wersję z nowszą datą (bot).
5. Nie force-pushuj „żeby posprzątać" bez potrzeby — historia append-only jest
   bezpieczna; force-push tylko jeśli faktycznie coś się u double.
   Nigdy nie usuwaj commitów bot-raportów ani pracy faz 0–2.1.

## 2. Wiedza operacyjna o środowisku (zebrane blizny)

1. **Sandbox resetuje się między turami** (nowy .git, refspec tylko main;
   fix: `git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"`).
   Worktree zwykle przetrwał przez snapshot — ale ZAWSZE najpierw kwarantanna.
2. **Push bywa bez poświadczeń** (token aplikacji Areny wygasa): wtedy poproś
   operatora o reconnect GitHub w Arena. Nigdy nie proś o tokeny do czatu.
3. **Nie da się pisać `.github/workflows/`** (aplikacja bez uprawnienia
   `workflows`): żywy plik wkleja operator przez UI (źródło prawdy:
   `docs/ci-workflow.yml`). Od teraz pilnuje tego test `test_workflow_drift`.
4. **Artefakty/logi CI (blob Azure) są NIEosiągalne** z sandboxa nawet przy
   publicznym repo. Dlatego workflow robi **bot-commit raportów** do brancha
   (`examples/spike/report/*.md`) — czytaj je przez contents-API. Runy/kroki/
   adnotacje czytasz przez actions-API (publiczne).
5. **Brak toolchainu Rust lokalnie** (ADR-0004): kod Rust pisany „na ślepo",
   kompiluje CI. Dlatego: różne sieci bezpieczeństwa (cień+golden+CI) i
   cierpliwa pętla „push→czerwono→fix". Krytyczne zasady fmt: diff z CI
   stosuj 1:1; długie stringi/komentarze rustfmt zostawia; kolejność itemów
   alfabetyczna (`pub mod cluster` przed `pub mod ffi`).
6. **Sieć**: crates.io/rust-lang/bloki Azure — wycięte. Dostępne: github.com,
   codeload, api.github, PyPI. Instalacje pip: `--break-system-packages`.

## 3. Sukcesy (twarde liczby; szczegóły w REPORT.md)

* Differential: **1784 przypadki, 0 rozbieżności** (L1 replay z prawdziwej
  suite + L2 seedowane + l1-trace z manifestu).
* Liście-podstawy przez ctypes: slug ~6,9×, uuid ~4,6×, ipv4 ~8,5–11,9×.
* **Klastry (2 niezależne runery)**: wariant LIŚCIE (2×FFI) = **7–8× WOLNIEJ
  niż python** (patologia potwierdzona); KLASTER (1×FFI) = **2,5× szybciej
  niż liście**; trywialny region = uczciwy NOT-WORTH (skala werdyktów działa).
* **9 bugów złapanych przez 9 różnych warstw** (tabela w REPORT) — żaden
  nie przetrwał kontaktu z pipeline'em; to jest jądro metody projektu.
* CI zielone end-to-end, raporty self-serve, bot-commit działa.

## 4. Błędy/lekcje (żebyś nie powtarzał)

* Bugi #1–#9: patrz REPORT (kompilacja ×3, złe oczekiwanie testu z probe'u
  o innych parametrach, `?` mylące „błąd parsowania" z „poza kontraktem",
  `bool(None)` w kleju ctypes, sys.path pakiet-vs-rodzic, E0603 prywatność,
  unused_parens z generatora).
* **Moje błędy procesowe** (najboleśniejsze): (a) `git reset --hard` po
  resecie sandboxa zamiast kwarantanny → utrata modyfikacji plików
  śledzonych; (b) rebase rozstrzygnięty `--ours` (= stara wersja zdalna!)
  → commit rayona wjechał pusty, operator wklejał słusznie stary plik;
  (c) zła ścieżka w teście (`../../` zamiast `../../../`) udawała fail
  drift-testu. Stąd: kwarantanna zawsze, `--theirs` dla moich, test ścieżek.

## 5. Kolejność działań w nowej sesji

1. Push lokalnych commitów (sekcja 1) → zielone CI (job Rust kompiluje
   rayon pierwszy raz — jeśli padnie, czytaj adnotacje; typowe: API pyo3 0.23).
2. **Przypomnij operatorowi o wklejce** `docs/ci-workflow.yml` → żywy
   `.github/workflows/ci.yml` (przez UI; drift-test sam zzielenieje).
3. Run mierzy rayona → odczytaj `examples/spike/report/bench-parallel.md`
   (bot-commit) → wpisz liczby do REPORT.md (odpowiedź na pytanie operatora
   „czy 20×?"). Nie obiecuj — mierz i zapisz, auch wenn NOT-WORTH.
4. Dalej wg PLAN.md: implementacja ADR-0006 (Unicode/slugify), upgrade
   pyo3 0.23→0.29, komenda `apply` (writer shimów), klastry multi-modułowe,
   packaging (maturin wheel).

## 6. Rytuały projektu (utrzymuj)

* Probe-first: żadnej reguły z dokumentacji — wszystko empirycznie wobec
  prawdziwego interpretera (złote reguły w REPORT §faza 0).
* Uczciwość raportu: NOT-WORTH to też wynik; never overselluj (operator
  docenia proste liczby, w tym te niewygodne).
* Commity po polsku, z „dlaczego"; [skip ci] dla botów; ADR przy każdej
  decyzji architektonicznej; manifesty/raporty = artefakty commitowane.
* Zasady Z1–Z7 i kontrakty K1–K8 (PLAN) — serce produktu; weryfikacja
  jest produktem, translator tylko backendem.
```

### PLIK: `examples/spike/pyo3/Cargo.toml`  (rayon-v2: moduł hotport_rs)
```python
[package]
name = "hotport-spike-pyo3"
version = "0.0.1"
edition = "2021"
license = "Apache-2.0"
description = "Spike: binding PyO3 + batch API z rayonem (budowane w CI)"

[lib]
name = "hotport_rs"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module", "abi3-py39"] }
rayon = "1.10"
hotport-spike-core = { path = "../core" }
```

### PLIK: `examples/spike/pyo3/src/lib.rs`  (rayon-v2: ipv4_batch + allow_threads)
```python
//! Binding PyO3 dla rdzenia spike'a (budowane w CI — ADR-0004).
//! Woła TE SAME funkcje co ścieżka ctypes; różnica to tylko koszt przejścia.

use pyo3::prelude::*;
use rayon::prelude::*;

/// Zwraca True/False albo None, gdy wejście jest poza kontraktem ASCII
/// (wtedy Python shim kieruje wywołanie do oryginału — Z5).
#[pyfunction]
fn slug_is_valid(value: &str) -> bool {
    hotport_spike_core::slug_core(value)
}

#[pyfunction]
fn uuid_is_valid(value: &str) -> Option<bool> {
    hotport_spike_core::uuid_core(value)
}

#[pyfunction]
fn ipv4_is_valid(value: &str, cidr: bool, strict: bool, host_bit: bool) -> Option<bool> {
    hotport_spike_core::ipv4_core(value, cidr, strict, host_bit)
}

/// BATCH API [rayon]: jedno przejście FFI na CAŁĄ listę + wszystkie rdzenie.
///
/// Kontrakt batcha (odmiana ADR-0005): elementy poza kontraktem ASCII dają
/// false (batch = szybka ścieżka; per-item routing nie ma sensu masowo).
/// `py.allow_threads` ZWALNIA GIL: pythonowe wątki żyją, rayon kręci się
/// na wszystkich rdzeniach (work-stealing).
#[pyfunction]
fn ipv4_batch(py: Python<'_>, items: Vec<String>) -> Vec<bool> {
    py.allow_threads(move || {
        items
            .into_par_iter()
            .map(|s| hotport_spike_core::ipv4_core(&s, true, false, true).unwrap_or(false))
            .collect()
    })
}

#[pymodule]
fn hotport_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(slug_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(uuid_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(ipv4_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(ipv4_batch, m)?)?;
    Ok(())
}
```

### PLIK: `examples/spike/tests/test_workflow_drift.py`  (anti-drift workflowa)
```python
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
    strict=False,
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
```

### PLIK: `docs/decisions/ADR-0006-unicode-slugify.md`  (decyzja Unicode)
```markdown
# ADR-0006: Unicode dla celu #2 (python-slugify) — dane jako dane

* Status: PROPOSED (2026-08-25, do realizacji po powrocie zdalnym)
* Kontekst: cel #2 ma `ascii_fraction = 0.593` — **40% prawdziwych wejść jest
  nie-ASCII** (slugify to biblioteka stricte unicode: PRE_TRANSLATIONS +
  unidecode). Kontrakt ASCII z ADR-0005 załatwia poprawność (routing), ale
  routowałby 40% hot-pathu — czyli obywałby się celu.

## Decyzja (tier-2 z PLAN §7.5): „dane jako dane, nie kod jako kod"

1. **PRE_TRANSLATIONS jako tabela**: skrypt eksportuje `slugify/special.py`
   do posortowanej tablicy `(char, &str)` w Rust (std-only: binary search;
   bez phf, bez zależności w core).
2. **Unicode lowercase**: w warstwie PyO3 przez crate `unicode-normalization`
   (core pozostaje std-only — jak rayon, właściwość crate'ów „ciężkich"
   ląduje w bindingu, nie w rdzeniu). Kontrakt rdzenia rozszerzony:
   `None` zostaje tylko dla nie-transliterowalnych/wejść spoza mapy.
3. **unidecode (pełna transliteracja alfabetów)**: za ciężkie na v1 —
   **routing per-input** do oryginału (slugify z unidecode i tak go wywołuje;
   nasz zysk zostaje na mapowanych znakach = większość realnych wejść).
4. **Differential**: suite vendora (82 testy, bogate unicode) + rozszerzone
   L2 (diakrytyki, CJK, emoji, znakicomposed vs decomposed — NFC/NFD
   to pułapka K2-klasyczna: normalization przed porównaniem!).

## Alternatywy odrzucone

* Pełny port unidecode (tysiące mapowań) — koszt >> zysk na v1.
* Rozszerzenie kontraktu ASCII o „cały Unicode w core" — psuje std-only rdzenia.

## Metryka sukcesu

`ascii_fraction` przestaje być metryką routing-u; nowa metryka: **ułamek
wejść obsłużonych przez rdzeń** (cel ≥ 0.9 na suite slugify) + speedup
≥ ×3 na promowanych funkcjach (NFD/NFC w raporcie jako osobny wiersz K2).
```

### PLIK: `examples/targets/demo_fns.py`  (cele demo (8 funkcji, w tym v0.1))
```python
"""Syntetyczny moduł-cel dla translatora v0 (Faza 2).

Funkcje ŚWIADOMIE napisane w podzbiorze v0 translatora (patrz
hotport_trans/translator.py: SUPPORTED_NODES) — to rig testowy reguł
translacji, odpowiednik tego, czym `validators` był dla fazy 0.

Podzbiór v0: adnotowane typy (int/float/str/bool), literale, arytmetyka
(+ - * na int z checked_* i float; / tylko float), porównania jednotypowe
(łańcuchowe rozwijane), and/or/not, if/elif/else, for-in-range, assign,
return na wszystkich ścieżkach; whitelist: len(str), abs(float), min/max,
str.startswith/endswith. Świadomie POZA v0: truthiness, //, %, **, wyjątki,
try/except, mixed int/float porównania, f-stringi, mutowalne kolekcje.
"""


def in_band(value: float, lo: float, hi: float) -> bool:
    """Czy value leży w [lo, hi] (porównania łańcuchowe)."""
    return lo <= value and value <= hi


def grade(points: float) -> int:
    """Próg punktowy → ocena (if/elif/else, return int)."""
    if points >= 90:
        return 5
    elif points >= 75:
        return 4
    elif points >= 60:
        return 3
    else:
        return 0


def sum_upto(n: int) -> int:
    """Suma 1..n (pętla range + checked_add; n trzymamy małe — to rig pętli)."""
    total = 0
    for i in range(1, n + 1):
        total = total + i
    return total


def safe_mul(a: int, b: int) -> int:
    """Iloczyn z kontrolą i64 (K3: overflow → checked_mul → routing). O(1) —
    to TU testujemy granice i64, bo oracle liczy bez pętli."""
    return a * b


def code_ok(code: str, prefix: str) -> bool:
    """Prosta walidacja kodu (len/startswith/endswitch + and/or)."""
    if len(code) != 10:
        return False
    return code.startswith(prefix) and not code.endswith("-")


def floor_div(a: int, b: int) -> int:
    """a // b — semantyka pythona: FLOOR (v0.1: helper __floordiv)."""
    return a // b


def py_mod(a: int, b: int) -> int:
    """a % b — znak DZIELNIKA (v0.1: helper __pymod)."""
    return a % b


def negate(a: int) -> int:
    """-a — checked (v0.1; -(i64::MIN) → routing)."""
    return -a
```

### PLIK: `examples/spike/python/hotport_trans/translator.py`  (translator v0.2+v0.1 (CAŁY plik))
```python
"""Translator deterministyczny v0 — podzbiór Pythona → Rust (+ cień Python).

Zasady (PLAN.md Z3, ADR-0003 — bez LLM):
* wejście: funkcja z adnotacjami typów, napisana w podzbiorze v0,
* wyjście A: **kod Rust** (tekst; kompilacja w CI — ADR-0004),
* wyjście B: **cień** — wygenerowany Python O TYCH SAMYCH regułach, z guardami
  semantyki Rust (i64 checked, brak truthiness), który DA SIĘ differentialowo
  zweryfikować już dziś wobec oryginału (metodologia ref-backend z fazy 0).

Każda reguła ma swój odpowiednik po obu stronach — cokolwiek innego niż
1:1 to bug translatora i MUSI wyjść w differentialu.
"""

import ast
import textwrap

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1

# ------------------------------------------------------------------ podzbiór

_BIN_INT = {"Add": "checked_add", "Sub": "checked_sub", "Mult": "checked_mul"}
_BIN_FLOAT = {"Add": "+", "Sub": "-", "Mult": "*", "Div": "/"}

# v0.1: operatory o INNEJ semantyce w Rust niz w Pythonie → helpery
# (python: floor + znak dzielnika; rust natywnie: trunc + znak dzielnej)
_BIN_INT_HELPERS = {
    "FloorDiv": ("__floordiv", "_floordiv"),  # a // b
    "Mod": ("__pymod", "_pymod"),              # a % b
}
_CMP = {"Lt": "<", "LtE": "<=", "Gt": ">", "GtE": ">=", "Eq": "==", "NotEq": "!="}


class UnsupportedNode(Exception):
    """Węzeł AST poza podzbiorem v0 — powód trafia do raportu (Z5)."""

    def __init__(self, fn, node, why):
        self.fn, self.why = fn, why
        super().__init__(
            f"{fn}: {type(node).__name__} (linia {getattr(node, 'lineno', '?')}) — {why}"
        )


class TranslationError(Exception):
    pass


_TYPE_MAP = {"int": "i64", "float": "f64", "str": "&str", "bool": "bool"}


def _ann(node, fn):
    if isinstance(node, ast.Name) and node.id in _TYPE_MAP:
        return _TYPE_MAP[node.id]
    raise UnsupportedNode(fn, node, f"adnotacja {ast.dump(node)[:40]} poza v0 (dozwolone: int/float/str/bool)")


def _returns_always(body):
    for st in body:
        if isinstance(st, ast.Return):
            return True
        if isinstance(st, ast.If) and st.orelse and _returns_always(st.body) and _returns_always(st.orelse):
            return True
    return False


class _FnTranslator:
    def __init__(self, fndef, known=None):
        self.fn = fndef.name
        self.fndef = fndef
        self.vars = {}  # nazwa -> typ ("i64"/"f64"/...)
        self.args = []  # [(name, ty)]
        # v0.2 [REVIEW pkt 8-9]: znane funkcje modułu => dozwolone wywołania
        # wewnętrzne (klastry). known: name -> ([typy arg], typ wyniku)
        self.known = known or {}
        self.used_helpers = set()  # v0.1: helpery semantyczne użyte w funkcji
        self.ret = _ann(fndef.returns, self.fn) if fndef.returns else None
        if self.ret is None:
            raise UnsupportedNode(self.fn, fndef, "brak adnotacji zwracanego typu (wymagana w v0)")
        # nazwy przypisywane więcej niż raz → wymagają `mut` w deklaracji
        from collections import Counter
        counts = Counter(
            t.id
            for st in ast.walk(ast.Module(body=fndef.body, type_ignores=[]))
            if isinstance(st, ast.Assign)
            for t in st.targets
            if isinstance(t, ast.Name)
        )
        self.mutable = {n for n, k in counts.items() if k > 1}

    # ---------------------------------------------------------- wyrażenia

    def expr(self, e):
        """→ (rust, py, typ). Każda gałąź utrzymuje parę 1:1."""
        fn = self.fn
        if isinstance(e, ast.Constant):
            if isinstance(e.value, bool):
                return ("true" if e.value else "false", "True" if e.value else "False", "bool")
            if isinstance(e.value, int):
                if not (I64_MIN <= e.value <= I64_MAX):
                    raise UnsupportedNode(fn, e, f"literał int {e.value} poza i64 (K3)")
                return (str(e.value), str(e.value), "i64")
            if isinstance(e.value, float):
                return (repr(e.value), repr(e.value), "f64")
            if isinstance(e.value, str):
                r = '"' + e.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
                return (r, repr(e.value), "&str")
            raise UnsupportedNode(fn, e, f"literał {type(e.value).__name__} poza v0")
        if isinstance(e, ast.Name):
            ty = self.vars.get(e.id)
            if ty is None:
                raise UnsupportedNode(fn, e, f"nieznana zmienna {e.id!r} (brak deklaracji w v0)")
            return (e.id, e.id, ty)
        if isinstance(e, ast.BinOp):
            op = type(e.op).__name__
            l, lp, lt = self.expr(e.left)
            r, rp, rt = self.expr(e.right)
            if lt == "i64" and rt == "i64":
                if op in _BIN_INT_HELPERS:
                    rs_name, py_name = _BIN_INT_HELPERS[op]
                    self.used_helpers.add(rs_name)
                    return (
                        f"{rs_name}({l}, {r})?",
                        f"{py_name}({lp}, {rp})",
                        "i64",
                    )
                if op not in _BIN_INT:
                    raise UnsupportedNode(fn, e, f"operator {op} na int poza v0 (** → patrz dokumentacja pułapek)")
                rust = f"({l}).{_BIN_INT[op]}({r})?"
                return (rust, f"_bin('{op[0].lower()}', {lp}, {rp})", "i64")
            # dowolna strona float → f64 (int koercja jawna; mixed ==/porównania odrzucane niżej)
            if "f64" in (lt, rt) and lt in ("i64", "f64") and rt in ("i64", "f64"):
                opf = _BIN_FLOAT.get(op)
                if opf is None:
                    raise UnsupportedNode(fn, e, f"operator {op} na float poza v0")
                lr = f"(({l}) as f64)" if lt == "i64" else f"({l})"
                rr = f"(({r}) as f64)" if rt == "i64" else f"({r})"
                # cień MUSI symulować koercję rustową (as f64 = zaokrąglenie do najbliższej
                # wartości f64) — dlatego float() po stronie pythonowej inta. Oracle python
                # liczy mixed dokładnie, więc różnica na wielkich intach WYJDZIE w differentialu (K2).
                lpr = f"float({lp})" if lt == "i64" else f"({lp})"
                rpr = f"float({rp})" if rt == "i64" else f"({rp})"
                return (f"{lr} {opf} {rr}", f"({lpr} {opf} {rpr})", "f64")
            raise UnsupportedNode(fn, e, f"BinOp {lt} {op} {rt} poza v0 (tylko i64×i64 / f64)")
        if isinstance(e, ast.UnaryOp):
            if isinstance(e.op, ast.Not):
                v, vp, vt = self.expr(e.operand)
                if vt != "bool":
                    raise UnsupportedNode(fn, e, "not na nie-bool (truthiness poza v0)")
                return (f"!({v})", f"(not {vp})", "bool")
            if isinstance(e.op, ast.USub):
                v, vp, vt = self.expr(e.operand)
                if vt == "f64":
                    return (f"-({v})", f"-({vp})", "f64")
                if vt == "i64":
                    # v0.1: checked_neg — -(i64::MIN) przepełnia → routing (python liczy dalej)
                    self.used_helpers.add("__neg")
                    return (f"__neg({v})?", f"_neg({vp})", "i64")
                raise UnsupportedNode(fn, e, "unarne minus na nie-numery poza v0")
            raise UnsupportedNode(fn, e, "UnaryOp poza v0")
        if isinstance(e, ast.BoolOp):
            op = "&&" if isinstance(e.op, ast.And) else "||"
            pop = " and " if op == "&&" else " or "
            parts, pparts = [], []
            for v in e.values:
                r, p, t = self.expr(v)
                if t != "bool":
                    raise UnsupportedNode(fn, e, f"BoolOp na {t} (truthiness poza v0 — jawny warunek bool wymagany)")
                parts.append(f"({r})")
                pparts.append(f"({p})")
            return (f" {op} ".join(parts), pop.join(pparts), "bool")
        if isinstance(e, ast.Compare):
            left, leftp, leftt = self.expr(e.left)
            leftn = e.left  # potrzebny node do reguły literału poniżej
            rs, rps = [], []
            cur, curp, curt, curn = left, leftp, leftt, leftn
            for op, comp in zip(e.ops, e.comparators):
                r, rp, rt = self.expr(comp)
                o = _CMP.get(type(op).__name__)
                if o is None:
                    raise UnsupportedNode(fn, e, f"porównanie {type(op).__name__} poza v0 (is None → v0.1)")
                if curt == rt and curt in ("i64", "f64", "bool", "&str"):
                    pass  # jednotypowe — bez zmian
                elif {curt, rt} == {"i64", "f64"}:
                    # mixed DOZWOLONE tylko gdy strona int jest LITERAŁEM ≤2^53
                    # (dokładnie reprezentowalny w f64; python porównuje wartościowo,
                    #  więc wynik identyczny). Int zmienna → odrzucamy (koercja f64
                    # dużych intów gubi precyzję — pułapka K2).
                    node = curn if curt == "i64" else comp
                    if not (isinstance(node, ast.Constant) and isinstance(node.value, int)
                            and abs(node.value) <= 2**53):
                        raise UnsupportedNode(
                            fn, e,
                            "porównanie mixed int/float dozwolone w v0 tylko dla literału int ≤2^53 "
                            "(python porównuje wartościowo; koercja f64 gubi precyzję — K2)",
                        )
                    if curt == "i64":
                        cur = repr(float(cur))  # 90 → 90.0 (rust)
                    else:
                        r = repr(float(r))
                else:
                    raise UnsupportedNode(fn, e, f"porównanie {curt} {o} {rt} poza v0")
                rs.append(f"({cur}) {o} ({r})")
                rps.append(f"({curp}) {o} ({rp})")
                cur, curp, curt, curn = r, rp, rt, comp
            return (" && ".join(rs), " and ".join(rps) if len(rs) > 1 else rps[0], "bool")
        if isinstance(e, ast.Call):
            return self.call(e)
        raise UnsupportedNode(fn, e, "wyrażenie poza podzbiorem v0")

    def call(self, e):
        fn = self.fn
        # v0.2: wywołania funkcji modułu (klastry) — jedno przejście FFI na cały
        # łańcuch: rust woła wnętrza bezpośrednio (`?` rozpakowuje Option),
        # cień przez _call (None z wnętrza = _Out, dokładnie jak `?` w rust).
        if isinstance(e.func, ast.Name) and e.func.id in self.known:
            argtys, retty = self.known[e.func.id]
            if len(e.args) != len(argtys) or e.keywords:
                raise UnsupportedNode(fn, e, f"wywołanie {e.func.id}: tylko pozycyjne, pełna arność")
            pairs = [self.expr(a) for a in e.args]
            for (_, _, got), want in zip(pairs, argtys):
                if got != want:
                    raise UnsupportedNode(fn, e, f"wywołanie {e.func.id}: typ {got} ≠ {want}")
            # bez opakowania w nawiasy: rustc ostrzega unused_parens przy
            # prostych identyfikatorach (bug #9 z logow CI)
            rust_args = ", ".join(rc for rc, _, _ in pairs)
            py_args = ", ".join(pc for _, pc, _ in pairs)
            return (
                f"{e.func.id}({rust_args})?",
                f"_call({e.func.id}, {py_args})",
                retty,
            )
        # len(s)
        if isinstance(e.func, ast.Name) and e.func.id == "len" and len(e.args) == 1:
            v, vp, vt = self.expr(e.args[0])
            if vt != "&str":
                raise UnsupportedNode(fn, e, f"len() na {vt} — tylko str w v0")
            # PUŁAPKA: python len(str) = pkt kodowe; rust s.len() = BAJTY → chars().count()
            return (f"({v}).chars().count()", f"len({vp})", "i64")
        # abs/min/max — tylko float w v0
        if isinstance(e.func, ast.Name) and e.func.id in ("abs", "min", "max"):
            args = [self.expr(a) for a in e.args]
            if not (1 <= len(args) <= 2):
                raise UnsupportedNode(fn, e, "abs/min/max: 1-2 argumenty w v0")
            if any(t != "f64" for _, _, t in args):
                raise UnsupportedNode(fn, e, "abs/min/max na nie-float poza v0")
            codes = [c for c, _, _ in args]
            pcodes = [p for _, p, _ in args]
            if e.func.id == "abs":
                return (f"({codes[0]}).abs()", f"abs({pcodes[0]})", "f64")
            m = "min" if e.func.id == "min" else "max"
            return (f"({codes[0]}).{m}({codes[1]})", f"{m}({pcodes[0]}, {pcodes[1]})", "f64")
        # metody str: startswith/endswith → starts_with/ends_with (mapowanie nazw!)
        _STR_METHODS = {"startswith": "starts_with", "endswith": "ends_with"}
        if isinstance(e.func, ast.Attribute) and e.func.attr in _STR_METHODS:
            base, basep, bt = self.expr(e.func.value)
            if bt != "&str" or len(e.args) != 1:
                raise UnsupportedNode(fn, e, f".{e.func.attr} w v0: tylko str × 1 arg")
            a, ap, at = self.expr(e.args[0])
            if at != "&str":
                raise UnsupportedNode(fn, e, f".{e.func.attr}({at}) — tylko str")
            m = _STR_METHODS[e.func.attr]
            return (f"({base}).{m}({a})", f"{basep}.{e.func.attr}({ap})", "bool")
        raise UnsupportedNode(fn, e, f"wywołanie poza whitelistą v0: {ast.dump(e.func)[:50]}")

    # ---------------------------------------------------------- instrukcje

    def stmts(self, body, indent, rust_out, py_out, py_indent):
        pad, ppad = "    " * indent, "    " * py_indent
        for st in body:
            if isinstance(st, ast.Return):
                v, vp, vt = self.expr(st.value) if st.value else (None, None, None)
                if vt != self.ret:
                    raise UnsupportedNode(self.fn, st, f"return {vt}, deklarowano {self.ret}")
                rust_out.append(f"{pad}return Some({v});")
                py_out.append(f"{ppad}return {vp};")
            elif isinstance(st, ast.Assign):
                if len(st.targets) != 1 or not isinstance(st.targets[0], ast.Name):
                    raise UnsupportedNode(self.fn, st, "Assign: pojedyncza nazwa w v0")
                name = st.targets[0].id
                v, vp, vt = self.expr(st.value)
                if name in self.vars:
                    # PONOWNE przypisanie: typ musi się zgadzać (v0: stała typizacja),
                    # emitujemy PRZYPISANIE (nie let — pułapka znaleziona w v0: pierwotny
                    # emitter generował `let`, co w Rust daje shadowing zamiast update'u)
                    if vt != self.vars[name]:
                        raise UnsupportedNode(self.fn, st, f"zmienna {name} zmienia typ {self.vars[name]}→{vt} (v0: zabronione)")
                    rust_out.append(f"{pad}{name} = {v};")
                else:
                    self.vars[name] = vt
                    mut = "mut " if name in self.mutable else ""
                    rust_out.append(f"{pad}let {mut}{name}: {_rs_ty(vt)} = {v};")
                py_out.append(f"{ppad}{name} = {vp};")
            elif isinstance(st, ast.If):
                t, tp, tt = self.expr(st.test)
                if tt != "bool":
                    raise UnsupportedNode(self.fn, st, f"if-test {tt} (truthiness poza v0)")
                rust_out.append(f"{pad}if {t} {{")
                py_out.append(f"{ppad}if {tp}:")
                self.stmts(st.body, indent + 1, rust_out, py_out, py_indent + 1)
                if st.orelse:
                    # elif = zagnieżdżony If — rozwiń dla ładnego Rusta
                    if len(st.orelse) == 1 and isinstance(st.orelse[0], ast.If):
                        self._elif(st.orelse[0], indent, rust_out, py_out, py_indent)
                    else:
                        rust_out.append(f"{pad}}} else {{")
                        py_out.append(f"{ppad}else:")
                        self.stmts(st.orelse, indent + 1, rust_out, py_out, py_indent + 1)
                        rust_out.append(f"{pad}}}")
                else:
                    rust_out.append(f"{pad}}}")
            elif isinstance(st, ast.For):
                if (not isinstance(st.iter, ast.Call) or not isinstance(st.iter.func, ast.Name)
                        or st.iter.func.id != "range" or not 1 <= len(st.iter.args) <= 2):
                    raise UnsupportedNode(self.fn, st, "For: tylko range(a, b) / range(n) w v0")
                tgt = st.target
                if not isinstance(tgt, ast.Name):
                    raise UnsupportedNode(self.fn, st, "For-target: pojedyncza nazwa")
                rng = [self.expr(a) for a in st.iter.args]
                if any(t != "i64" for _, _, t in rng):
                    raise UnsupportedNode(self.fn, st, "range() na nie-int")
                lo = ("0", "0") if len(rng) == 1 else (rng[0][0], rng[0][1])
                hi = (rng[-1][0], rng[-1][1])
                self.vars[tgt.id] = "i64"
                rust_out.append(f"{pad}for {tgt.id} in ({lo[0]})..({hi[0]}) {{")
                py_out.append(f"{ppad}for {tgt.id} in range({lo[1]}, {hi[1]}):")
                self.stmts(st.body, indent + 1, rust_out, py_out, py_indent + 1)
                rust_out.append(f"{pad}}}")
            else:
                raise UnsupportedNode(self.fn, st, f"instrukcja {type(st).__name__} poza v0")

    def _elif(self, ifnode, indent, rust_out, py_out, py_indent):
        pad, ppad = "    " * indent, "    " * py_indent
        t, tp, tt = self.expr(ifnode.test)
        rust_out.append(f"{pad}}} else if {t} {{")
        py_out.append(f"{ppad}elif {tp}:")
        self.stmts(ifnode.body, indent + 1, rust_out, py_out, py_indent + 1)
        if ifnode.orelse:
            if len(ifnode.orelse) == 1 and isinstance(ifnode.orelse[0], ast.If):
                self._elif(ifnode.orelse[0], indent, rust_out, py_out, py_indent)
            else:
                rust_out.append(f"{pad}}} else {{")
                py_out.append(f"{ppad}else:")
                self.stmts(ifnode.orelse, indent + 1, rust_out, py_out, py_indent + 1)
                rust_out.append(f"{pad}}}")
        else:
            rust_out.append(f"{pad}}}")

    # ---------------------------------------------------------- całość

    def translate(self):
        f = self.fndef
        for a in f.args.args:
            if a.annotation is None:
                raise UnsupportedNode(self.fn, a, "argument bez adnotacji typu (wymagana w v0)")
            ty = _ann(a.annotation, self.fn)
            self.args.append((a.arg, ty))
            self.vars[a.arg] = ty
        if f.args.kwonlyargs or f.args.vararg or f.args.kwarg or f.args.defaults or f.args.posonlyargs:
            raise UnsupportedNode(self.fn, f, "v0: tylko pozycyjne argumenty bez defaultów")

        body = f.body
        # docstring to ast.Expr — pomijamy (to nie instrukcja wykonawcza)
        if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]

        rust, py = [], []
        self.stmts(body, 1, rust, py, 1)
        if not _returns_always(body):
            raise UnsupportedNode(self.fn, f, "nie wszystkie ścieżki возвращają (wymagane w v0)")

        sig_r = ", ".join(f"{n}: {_rs_ty(t)}" for n, t in self.args)
        head_r = f"/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ\npub fn {self.fn}({sig_r}) -> Option<{_rs_ty(self.ret)}> {{"
        tail_r = "    Some(<ostatnie wyrażenie jest w return powyżej>)\n}"  # nieistotne — return-y są wyczerpujące
        body_r = "\n".join(rust)
        # usuń atrapę: wszystkie ścieżki mają return — wystarczy pusty fallback na potrzeby kompilatora
        code_rust = f"{head_r}\n{body_r}\n}}\n"

        guards = [f"        if not ({I64_MIN} <= {n} <= {I64_MAX}): raise _Out()" for n, t in self.args if t == "i64"]
        sig_p = ", ".join(n for n, _ in self.args)
        code_py = (
            f"def {self.fn}({sig_p}):\n"
            f"    try:\n"
            + ("\n".join(guards) + "\n" if guards else "")
            + "\n".join("    " + l for l in py) + "\n"
            f"    except _Out:\n        return None\n"
        )
        return {
            "name": self.fn,
            "rust": code_rust,
            "shadow": code_py,
            "helpers": sorted(self.used_helpers),
        }


def _rs_ty(t):
    return {"i64": "i64", "f64": "f64", "bool": "bool", "&str": "&str"}[t]


SHADOW_PRELUDE = f'''# WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
# Cień = te same reguły translacji co kod Rust, wykonywalne w Pythonie:
# * int: arytmetyka _bin z kontrolą zakresu i64 (K3) — przekroczenie → _Out → None (routing),
# * brak truthiness — warunki jawnie bool,
_I64_MIN = {I64_MIN}
_I64_MAX = {I64_MAX}


class _Out(Exception):
    pass


def _chk(r):
    if not (_I64_MIN <= r <= _I64_MAX):
        raise _Out()
    return r


def _bin(op, a, b):
    if op == 'a':
        return _chk(a + b)
    if op == 's':
        return _chk(a - b)
    if op == 'm':
        return _chk(a * b)
    raise AssertionError(op)


def _floordiv(a, b):
    # python: floor + ZeroDivisionError; cien: b==0 -> _Out (routing, jak '?' w rust)
    if b == 0:
        raise _Out()
    return _chk(a // b)


def _pymod(a, b):
    if b == 0:
        raise _Out()
    return _chk(a % b)


def _neg(a):
    return _chk(-a)


def _call(f, *args):
    # wywołanie wewnętrzne (v0.2 klastry): None z wnętrza = _Out —
    # lustrzane odbicie operatora `?` w generowanym rust
    r = f(*args)
    if r is None:
        raise _Out()
    return r

'''


RUST_HELPERS = {
    # Semantyka PYTHONA wierna: floor-div i modulo ze znakiem DZIELNIKA;
    # dzielnik 0 → None (routing; python rzuci ZeroDivisionError).
    "__floordiv": """/// a // b — semantyka pythona: FLOOR (rust natywnie: trunc)
fn __floordiv(a: i64, b: i64) -> Option<i64> {
    let q = a.checked_div(b)?;
    if (a % b != 0) && ((a < 0) != (b < 0)) {
        q.checked_sub(1)
    } else {
        Some(q)
    }
}""",
    "__pymod": """/// a % b — semantyka pythona: znak DZIELNIKA (rust: znak dzielnej)
fn __pymod(a: i64, b: i64) -> Option<i64> {
    let r = a.checked_rem(b)?;
    if r != 0 && ((r < 0) != (b < 0)) {
        r.checked_add(b)
    } else {
        Some(r)
    }
}""",
    "__neg": """/// -a — checked (-(i64::MIN) przepełnia → routing)
fn __neg(a: i64) -> Option<i64> {
    a.checked_neg()
}""",
}


def translate_module(source, filename="<source>"):
    """→ {"functions": [Translation], "rejected": [(fn, powód)]}."""
    tree = ast.parse(source, filename=filename)
    out, rejected = [], []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        try:
            out.append(_FnTranslator(node).translate())
        except UnsupportedNode as e:
            rejected.append((node.name, str(e)))
    helpers = set()
    for t in out:
        helpers.update(t["helpers"])
    rust_helpers = "\n\n".join(RUST_HELPERS[h] for h in sorted(helpers))
    return {
        "functions": out,
        "rejected": rejected,
        "helpers": rust_helpers,
    }


def shadow_module_source(translations):
    parts = [SHADOW_PRELUDE]
    for t in translations:
        parts.append("\n\n" + t["shadow"])
    return "".join(parts)


def translate_cluster(source, entry, filename="<cluster>"):
    """v0.2 [REVIEW pkt 8-9]: przetłumacz REGION call-graph jako jedną całość.

    Domknięcie przejściowe wywołań z `entry` (tylko Name-calle do funkcji
    modułu). Emituje: entry jako `pub fn`, wnętrza jako prywatne `fn` —
    wywołania wewnętrzne w rust są darmowe, FFI płaci się RAZ (na wejściu).
    Rekurencja → UnsupportedNode.
    """
    tree = ast.parse(source, filename=filename)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    if entry not in fns:
        raise KeyError(f"nie ma funkcji {entry!r} w {filename}")

    known = {}
    for name, node in fns.items():
        argtys = []
        for a in node.args.args:
            if a.annotation is None:
                raise UnsupportedNode(name, node, "argument bez adnotacji (wymagana w v0)")
            argtys.append(_ann(a.annotation, name))
        if node.returns is None:
            raise UnsupportedNode(name, node, "brak adnotacji wyniku (wymagana w v0)")
        known[name] = (argtys, _ann(node.returns, name))

    order, seen = [], set()
    todo = [entry]
    while todo:
        name = todo.pop(0)
        if name in seen:
            continue
        seen.add(name)
        order.append(name)
        for sub in ast.walk(fns[name]):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in fns:
                if sub.func.id == name:
                    raise UnsupportedNode(name, fns[name], "rekurencja poza v0")
                todo.append(sub.func.id)

    translations = [_FnTranslator(fns[name], known=known).translate() for name in order]
    rust_parts = []
    for t in translations:
        r = t["rust"]
        if t["name"] != entry:
            # pub(crate): niewidoczne z zewnątrz crate'a, ale dostępne dla
            # naszego ffi.rs (bug #8 z CI: czysto prywatne `fn` → E0603)
            r = r.replace("pub fn", "pub(crate) fn", 1)
        rust_parts.append(r)
    helpers = set()
    for t in translations:
        helpers.update(t["helpers"])
    helper_src = "\n\n".join(RUST_HELPERS[h] for h in sorted(helpers))
    rust_all = "\n".join(rust_parts)
    if helper_src:
        rust_all = helper_src + "\n\n" + rust_all
    return {
        "entry": entry,
        "members": order,
        "rust": rust_all,
        "shadow": "\n\n".join(t["shadow"] for t in translations),
    }
```

### EDYCJA: `examples/spike/python/hotport_spike/gen.py` (v0.1)
W funkcji `demo_cases`, PRZED linią ze stratyfikowanymi krawędziami mnożenia
dodaj blok: div_edges = [(-7,2),(7,-2),(-7,-2),(7,2),(-1,5),(1,-5),(0,3),(3,1),
(1,0),(0,0),(-9,3),(2**62,2),(-(2**62),2),(-(2**63),-1),(2**63-1,2)];
for a,b in div_edges: add("floor_div",a,b); add("py_mod",a,b);
for a in [0,1,-1,5,-(2**63),2**62,2**63-1,2**63]: add("negate",a)

### EDYCJA: `examples/spike/python/hotport_spike/runner.py` (v0.1)
W `compare`, w gałęzi `if fn in _EXTRA_PY:` po klauzuli o wyniku poza i64
dopisz (osobna linia, nie w kontynuacji wyrażenia!):
    justified = justified or py.startswith("raise:ZeroDivisionError")

### EDYCJA: `examples/spike/tests/test_translator.py` (v0.1)
_DEMO_NAMES rozszerz o "floor_div","py_mod","negate"; dodaj test
test_zlote_reguly_emisji_v01 sprawdzający __floordiv/__pymod/__neg
w rust+helpers (wzorce: "__floordiv", "checked_rem", "checked_neg").

### EDYCJA: `examples/spike/python/hotport_trans/__main__.py`
Po `translate_module(...)` w trybie singles zapisz `result["helpers"]`
do generated/helpers.rs (jeśli niepuste).

### NA SAM KOŃIEC (po zielonym CI!): docs/ci-workflow.yml
3 zmiany: (a) Upload .so: path z DWIEMA liniami target/release/
libhotport_spike_core.so i target/release/libhotport_rs.so; (b) w kroku
"Rozmieść .so" dodaj: cp ci-artifacts/libhotport_rs.so
examples/spike/python/hotport_rs.so; (c) po "Benchmark przed/po" nowy krok
"Benchmark równoległy (rayon batch vs ProcessPool)" uruchamiający
examples/spike/python/hotport_spike/bench_parallel.py. Operator wkleja
przez UI po Twoim zielonym runie — przypomnij mu!
