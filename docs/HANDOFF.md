# HANDOFF — briefing dla nowej sesji (przeczytaj jako PIERWSZY)

> Kontekst: ten plik pisze agent sesji kończącej się 2026-08-25 dla agenta
> sesji następnej (projekt **hotport**, repo `peteraangelic-pixel/C_Rust`,
> branch `arena/01a03364-c-rust`). Po tej lekturze: PLAN.md (plan+postępy)
> i REPORT.md (kronika z liczbami).

## 1. Stan repozytorium (krytyczne!)

* **GitHub (pewne)**: cała praca do commitu `e106caa` — fazy 0–2.1: plan,
  spike validators (13 złotych reguł), tracer (manifest 0.2.0 z call-graph),
  translator v0.2 z KLASTRAMI, zielone CI z bot-commitami raportów,
  pomiar „region vs liście". Repo PUBLICZNE (API czytane bez tokena).
* **Lokalnie (być może w Twoim workspace)**: commity niewypchnięte (sesja
  zgasła na pushu): **rayon-v2** (moduł PyO3 `hotport_rs` z `ipv4_batch`,
  bench_parallel, test_parallel), **translator v0.1** (`//`, `%`, neg z
  semantyką pythona: helpery `__floordiv`/`__pymod`/`__neg`), **ADR-0006**
  (Unicode dla slugify), **test_workflow_drift**. Znaczniki: `rayon` w
  `examples/spike/pyo3/Cargo.toml`, `__floordiv` w translatorze,
  `docs/decisions/ADR-0006*`, `tests/test_workflow_drift.py`.
* **UWAGA — main vs branch**: platforma Arena przy zamknięciu sesji
  scalając PR mogła zostawić main 2 commity przed branchem (zobacz
  `git fetch && git log origin/main`). Zrekoncyliuj (rebase/cherry-pick)
  zanim zaczniesz cokolwiek nowego.
* **Procedura startowa**: `git fetch origin`; jeśli lokalne HEAD ma commity
  spoza origin → **kwarantanna najpierw** (`git add -A && git commit`), potem
  `git rebase origin/arena/01a03364-c-rust`; konflikty: pliki
  `examples/spike/report/*` → wersja zdalna (bot), cała reszta → **moje**
  (uwaga: w rebase `--theirs` = przybywające/moje zmiany!). Potem push.

## 2. Wiedza operacyjna o środowisku (blizny)

1. **Sandbox resetuje się między turami** (nowy .git, refspec tylko main;
   fix: `git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"`).
   Worktree zwykle przetrwał przez snapshot — ale ZAWSZE najpierw kwarantanna.
2. **Push bywa bez poświadczeń** (token aplikacji Areny wygasa): poproś
   operatora o reconnect GitHub w Arena. Nigdy nie proś o tokeny do czatu.
3. **Nie da się pisać `.github/workflows/`** (aplikacja bez uprawnienia
   `workflows`): żywy plik wkleja operator przez UI (źródło prawdy:
   `docs/ci-workflow.yml`). Pilnuje tego test `test_workflow_drift`.
4. **Artefakty/logi CI (blob Azure) NIEosiągalne** z sandboxa nawet przy
   publicznym repo. Workflow robi **bot-commit raportów** do brancha
   (`examples/spike/report/*.md`) — czytaj przez contents-API; runy/kroki/
   adnotacje przez actions-API.
5. **Brak toolchainu Rust lokalnie** (ADR-0004): Rust pisany „na ślepo",
   kompiluje CI. fmt: diff z CI stosuj 1:1; długie stringi/komentarze
   rustfmt zostawia; kolejność itemów alfabetyczna (`pub mod cluster`
   przed `pub mod ffi`).
6. **Sieć**: crates.io/rust-lang/bloki Azure — wycięte. Dostępne: github.com,
   codeload, api.github, PyPI. pip: `--break-system-packages`.

## 3. Sukcesy (szczegóły w REPORT.md)

* Differential: **1784 przypadki, 0 rozbieżności** (L1+L2+l1-trace).
* Liście przez ctypes: slug ~6,9×, uuid ~4,6×, ipv4 ~8,5–11,9×.
* **Klastry (2 runery)**: LIŚCIE (2×FFI) = **7–8× WOLNIEJ niż python**;
  KLASTER (1×FFI) = **2,5× szybciej niż liście**; trywialny region =
  uczciwy NOT-WORTH (skala werdyktów działa).
* **9 bugów / 9 warstw** (tabela w REPORT) — jądro metody projektu.
* CI zielone end-to-end; raporty self-serve przez bot-commit.

## 4. Błędy/lekcje

* Bugi #1–#9: REPORT.md (kompilacja ×3, oczekiwanie testu z probe'u o innych
  parametrach, `?` mylące „błąd parsowania" z „poza kontraktem", `bool(None)`
  w ctypes, sys.path pakiet-vs-rodzic, E0603, unused_parens z generatora).
* **Błędy procesowe agenta** (nie powtarzaj): (a) `git reset --hard` po
  resecie sandboxa zamiast kwarantanny → utrata zmian; (b) rebase rozwiązany
  `--ours` (= stara wersja!) → pusty commit rayona; (c) zła ścieżka w teście
  (`../../` zamiast `../../../`).

## 5. Kolejność działań w nowej sesji

1. Rekoncyliacja main↔branch (sekcja 1), push lokalnych commitów → zielone CI
   (rayon kompiluje się pierwszy raz; jeśli padnie — adnotacje; typowe: API pyo3 0.23).
2. **Przypomnij operatorowi o wklejce** `docs/ci-workflow.yml` → żywy
   `.github/workflows/ci.yml` (UI; drift-test sam zzielenieje).
3. Run mierzy rayona → odczytaj `examples/spike/report/bench-parallel.md`
   (bot-commit) → wpisz liczby do REPORT (pytanie operatora: „czy 20×?").
   Nie obiecuj — mierz i zapisz, auch wenn NOT-WORTH.
4. Dalej wg PLAN: ADR-0006 (Unicode/slugify), pyo3 0.23→0.29, komenda
   `apply` (writery shimów), klastry multi-modułowe, packaging (maturin).

## 6. Rytuały projektu (utrzymuj)

* Probe-first: żadnej reguły z dokumentacji — wszystko empirycznie wobec
  prawdziwego interpretera.
* Uczciwość raportu: NOT-WORTH to też wynik; never overselluj.
* Commity po polsku, z „dlaczego"; [skip ci] dla botów; ADR przy decyzjach
  architektonicznych; manifesty/raporty = artefakty commitowane.
* Zasady Z1–Z7 i kontrakty K1–K8 (PLAN) — weryfikacja jest produktem,
  translator tylko backendem.
