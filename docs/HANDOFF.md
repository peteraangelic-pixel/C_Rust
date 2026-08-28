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
