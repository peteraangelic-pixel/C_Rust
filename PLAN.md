# PLAN.md — „pyaccel" (nazwa robocza): przyspieszanie bibliotek Python przez zweryfikowany Rust

> Status: living document, v0.1 · Data: 2026-08-24 · Decyzja: opcja nr 1 z analizy —
> **Python hot-library → rozszerzenie Rust (PyO3) z zachowaniem API 1:1 i udowodnioną równoważnością.**
> Uwaga: „pyaccel" to placeholder — przed startem sprawdź dostępność na crates.io / PyPI / GitHub.

---

## 1. Wizja produktu

**Klient uruchamia jedną komendę na swojej bibliotece/aplikacji Python. Dostaje:**

1. Listę gorących funkcji (z profilowania i/lub wskazanych przez niego),
2. ich Rustowe implementacje jako drop-in zamiennik z **identycznym API**,
3. **raport równoważności** (dowód: nowy kod robi to samo na tysiącach wejść, w tym wygenerowanych automatycznie),
4. **benchmark przed/po** (czas, pamięć, startup) — czyli liczbę, którą można pokazać szefowi.

**Sprzedajemy przyspieszenie z dowodem, nie „Rusta".** Rust jest środkiem, nie celem.

### Zasady projektowe (nasze wytyczne — niczego tu nie łamiemy)

| # | Zasada | Skutek praktyczny |
|---|--------|-------------------|
| Z1 | **API 1:1, zawsze** | te same nazwy, kwargs, wartości domyślne, typy rzucanych wyjątków; testy klienta przechodzą bez zmian |
| Z2 | **Weryfikacja jest produktem** | każdy wygenerowany moduł ma raport z dowodem równoważności; bez dowodu → nie promujemy |
| Z3 | **Deterministyczny rdzeń, LLM jako generator hipotez** | struktura z AST + reguł; LLM tylko idiomatyzacja; wynik zawsze przez bramkę weryfikacji |
| Z4 | **Inkrementalnie, funkcja po funkcji** | przełącznik implementacji (python/rust/both) w runtime; migracja bez big-bang rewrite |
| Z5 | **Domyślnie „deny"** | jeśli nie umiemy udowodnić równoważności → funkcja zostaje w Pythonie + flaga do przeglądu przez człowieka (nigdy cicha różnica) |
| Z6 | **LLM opcjonalny, nie wymagany** | tryb no-cloud (reguły + lokalny model lub czysto deterministyczny) — powtarzalność w CI i zgodność klientów enterprise |
| Z7 | **Dowód wartości = raport** | benchmark i równoważność w jednym dokumencie (Markdown/HTML) |

---

## 2. Zakres MVP — świadomie wąski

### Do (in)
- **Czysty Python** (bez istniejących rozszerzeń C/Cythona w ścieżce tłumaczenia).
- **Zwykłe funkcje** modułowe: argumenty i wyniki z zamkniętego zbioru typów:
  `bool, int, float, str, bytes, None, list[T], tuple[T..], dict[K,V], Optional[T], Union (zamknięty)`, zagnieżdżone do głębokości ~3.
- Funkcje **deterministyczne, bez IO/sieci/czasu/losowości** (brak efektów zewnętrznych).
- Biblioteki z testami (lub dostarczonymi przykładami użycia) — potrzebne do harvestu wejść.
- Docelowa skala MVP: biblioteka do ~5–15 tys. LOC, tłumaczymy 3–10 gorących funkcji.

### Poza zakresem MVP (out — dopiero późniejsze fazy)
- klasy z dziedziczeniem, closures/dekoratory zmieniające sygnaturę, generatory, `async`,
- mutowalne argumenty z in-place semantyką (faza 2 — patrz kontrakty K4),
- funkcje z efektami zewnętrznymi, `random`/`time`/locale,
- `numpy`/pandas (to osobny, duży temat — data plane),
- cała aplikacja (nie biblioteka).

### Cele demonstracyjne (dogfooding, od najłatwiejszego)
1. **`validators`** — mała, czysta, świetne testy → idealny pierwszy cel.
2. **`python-slugify`** lub **`humanize`** — czysty Python, stringi, wrażliwe na edge case'y Unicode.
3. **`dateutil` (parser)** — gorąca pętla parsowania; pokazuje wartość fuzzingu (parser = klasyczny cel).

---

## 3. Architektura

```
                        ┌────────────────────────────────────────────────┐
                        │                 CLI (pyaccel)                  │
                        └────────────────────────────────────────────────┘
   profile ──►  [1] Tracer/Profiler (strona Pythona: cProfile, MonkeyType-style)
                     │  manifest.json  {funkcja, sygnatura, typy, częstość, call-graph}
                     ▼
   translate ─► [2] Translator      [3] Warstwa LLM (opcjonalna)
                     │  rdzeń deterministyczny (AST→Rust, mapa typów/stdlib)
                     │  + LLM idiomatyzacja + repair loop (rustc/clippy errors → poprawka)
                     ▼
                 [4] Generator bindingów PyO3  → moduł z przełącznikiem python|rust|both
                     │
                     ▼
   verify ────► [5] Silnik weryfikacji  ★ MOAT ★
                     │   L1 replay:  prawdziwe argumenty z testów klienta (record/replay)
                     │   L2 generacja: property-based (hypothesis-style) per kontrakt
                     │   L3 fuzzing:  mutacja wejść (parser-friendly), coverage-guided
                     │   + snapshot argumentów (m utacja), mapa wyjątków, tolerancja float
                     ▼
   bench ─────► [6] Benchmark harness (czas: criterion-style; pamięć; startup) + raport
```

### Komponenty i odpowiedzialności

| Komponent | Odpowiada za | Kluczowe decyzje |
|---|---|---|
| **[1] Tracer** (pakiet Python) | profil + inferencja typów argumentów/wyników, call-graph, harvest argumentów z testów | MonkeyType-style; limity rozmiaru zapisywanych obiektów; deterministyczne `repr` |
| **[2] Translator core** (Rust) | deterministyczna translacja szkieletu; **mapa typów** (`int→i64/i128 + OverflowError check`, `float→f64`, `str→String`, `bytes→Vec<u8>`, `list→Vec`, `dict→HashMap/IndexMap`) | `IndexMap` gdy zależna kolejność iteracji; bignum → jawny kontrakt K3 |
| **[2b] Mapa stdlib** | `str`→metody Rust, `re`→`regex`/`fancy-regex` (**tablica znanych różnic semantycznych!**), `datetime`→`chrono` (uwaga: kalendarze/strefy), `math`→`f64` metod y, `json`→`serde_json` (klucze: kolejność!), `itertools`→`itertools` crate | każde mapowanie z listą pułapek w dokumentacji |
| **[3] Warstwa LLM** | idiomatyzacja wygenerowanego szkieletu; prompt = kontrakt + typy + przykłady wejść/wyjść z testów | temperature 0, cache transakcji, brak LLM = ścieżka deterministyczna też musi działać (Z6) |
| **[4] Generator bindingów** | moduł PyO3 o identycznym API; wrapper z przełącznikiem `PYACCEL_IMPL=python\|rust\|both` | tryb `both` = kanarek produkcyjny (sampling + alarm przy różnicy) — killer feature zaufania |
| **[5] Silnik weryfikacji** | patrz sekcja 4 | rdzenie porównań w izolowanych procesach z timeoutem |
| **[6] Benchmark + raport** | przed/po (czas, pamięć, startup), tabelka funkcji: speedup ×, status weryfikacji | raport = artefakt commitowalny do CI |

### Struktura repo

```
crates/
  pyaccel-cli/        # CLI (clap), orkiestracja pipeline'u
  pyaccel-core/       # model manifestu, kontrakty, konfiguracja (serde, toml)
  pyaccel-trans/      # rdzeń translacji + mapa typów/stdlib
  pyaccel-verify/     # silnik differential/property/fuzz
  pyaccel-bench/      # harness benchmarkowy + generator raportu
py/
  pyaccel_tracer/     # tracer/inferencja/harvest (czysty Python)
examples/
  targets/validators/     # cel #1 (vendor, z licencją, tylko do testów)
  targets/python-slugify/
  targets/dateutil-parser/
docs/
  PLAN.md  contracts.md  stdlib-mapping.md  decisions/0001-*.md (ADR)
```

---

## 4. Silnik weryfikacji — serce produktu (★ moat)

### 4.1 Kontrakt równoważności per funkcja (deklaratywny, w manifestach)

| ID | Aspekt | Domyślna polityka |
|----|--------|-------------------|
| K1 | typy arg./wyniku | ścisła zgodność ze zbieranych typów (tracer) |
| K2 | wartość wyniku | deep-equality; **float**: tolerancja relatywna + ULP (konfigurowalna, domyślnie ścisła) |
| K3 | liczby całkowite | Python = bignum → domyślnie `i128` + check przepełnienia; overflow → **fail** kontraktu (nie ciche zawinięcie!) |
| K4 | mutacja argumentów | snapshot argów przed/po → porównanie (wykrywa in-place `sort`, `append`…); MVP: mutujące funkcje out-of-scope |
| K5 | wyjątki | ten sam typ (mapa: `ValueError`→`PyValueError`…) + zgodność „klasy komunikatu"; wyjątek po jednej stronie, wynik po drugiej → fail |
| K6 | przypadki brzegowe w generatorach | `None`, `""`, `"ńół"`, NaN, ±inf, −0.0, `0`, `-1`, `2**64`, puste kontenery, kolizje hash — **wbudowane seedy edge-case** |
| K7 | determinizm | funkcje niedeterministyczne (random/time) → poza zakresem lub wymóg injectowanego seeda/zegara |
| K8 | kolejność iteracji dict/set | `IndexMap`/`BTreeMap` zgodnie z zaobserwowaną semantyką; różnica → fail |

### 4.2 Trzy warstwy testów (rosnący koszt, rosnąca pewność)

1. **L1 — Replay (tanie, obowiązkowe):** tracer nagrywa prawdziwe argumenty z testów klienta → odtwarzamy na obu implementacjach → porównanie. Wykrywa ~większość oczywistych regresji.
2. **L2 — Property-based (średnie, obowiązkowe):** generatory wejść zbudowane z kontraktu typów (jak hypothesis strategies); seedowane — pełna powtarzalność w CI.
3. **L3 — Fuzzing (drogie, dla parserów):** mutacja stringów/bajtów z pokryciem (coverage-guided, cargo-fuzz na rdzeniu czystym od PyO3 lub mutacja na poziomie harnessu Pythona). Włączany per-funkcja flagą `fuzz = true`.

### 4.3 Bramka (gate) — reguły promocji

```
promuj funkcję do „rust"  ⇔  L1 100% PASS  ∧  L2 100% PASS (min. N=500 przypadków)
                                  ∧  K3–K8 bez naruszeń  ∧  benchmark ≥ próg (domyślnie ×1.5)
każda różnica → status DIFF → człowiek decyduje (Z5: nigdy auto-promocja z różnicą)
```

Wynik bramki jest **artefaktem** (`report.md` + JSON) — commitowalny, diffowalny w CI, z exit-code (0/1) do GitHub Actions.

### 4.4 Pułapki semantyczne — rejestrujemy od dnia 1 (checklista do code review)

- `re` Pythona ≠ `regex` crate w 100% (backreferences, lookbehind, semantyka Unicode) → tabela różnic + opcja fallbacku przez wywołanie do Pythona,
- `json`/`repr`: kolejność kluczy, `NaN/Infinity` w JSON,
- dzielenie całkowitoliczbowe vs. float (`/` zawsze float!), `//` dla ujemnych (floor),
- `int("١٢٣")` — Unicode digits; `str.strip()` bez argumentów vs. z argumentem,
- `sort` stabilność; `min/max` z NaN; `-0.0 == 0.0`,
- wyjątki: hierarchie (`LookupError` vs `KeyError/IndexError`), `except` łapiące nadklasę,
- GIL/FFI: koszt konwersji argumentów może **zjeść** zysk — patrz sekcja 6, ryzyko R4.

---

## 5. Stack technologiczny

| Warstwa | Wybór | Uzasadnienie / uwagi |
|---|---|---|
| Rdzeń + CLI | Rust, `clap`, `serde`, `toml`, `anyhow`/`thiserror`, `tracing` | standard, stabilne |
| Parsowanie Pythona | tree-sitter-python **lub** rustpython-parser | decyzja ADR-0002 (quick spike; tree-sitter = szybkość, rustpython = pełniejsze AST) |
| Bindingi | `pyo3` + `maturin`, wheels `abi3` (3.9+) | jeden wheel dla wszystkich wersji |
| Tracer | czysty Python (sys.setprofile + wrapper harvest) | zero zależności u klienta poza tymczasowym pakietem |
| Property-based | własne generatory w Rust (strategie z kontraktów) + opcja `hypothesis` w trybie python | determinizm i szybkość |
| Benchmark | `criterion` + `tracemalloc`-odpowiednik | raport przed/po |
| LLM | provider-agnostic (interfejs `Translator`), domyślnie OFF | temperature 0, cache, ADR-0003 |
| CI | GitHub Actions: testy crate'ów + pytest celów + gate na L1/L2 | dowód równoważności w CI od 1. dnia |

---

## 6. Plan działania (fazy, tygodnie, Definition of Done)

Założenie: 1 osoba, ~10–15 h/tydzień. Przy większym budżecie czasu fazy się nakładają.

### Faza 0 — Spike walidacyjny (tydz. 1) ⏱ 1 tyg. — **UKOŃCZONA 2026-08-24** (patrz REPORT.md)
- [x] Dostępność nazwy: **hotport** — PyPI wolne; crates.io do weryfikacji w CI (sandbox bez dostępu — ADR-0004); ADR-0001: Apache-2.0.
- [x] **Ręcznie** przetłumaczone 3 funkcje z `validators` (slug/uuid/ipv4): rdzeń Rust (std-only, FFI + PyO3 w CI) + wykonywalna specyfikacja `ref` zweryfikowana differentialowo: **1743 przypadki, 0 rozbieżności**; 5/5 wstrzykniętych bugów złapanych.
- [x] Szkic kontraktów (K1–K8 zrealizowane w kodzie: hotport-core/hotport-verify); format `manifest.json` — zostaje do fazy 1 (zamrożenie + serde).
- [x] ADR-0002 (parser — PROPOSED, decyzja w fazie 1) i ADR-0003 (LLM OFF w v1).
- **DoD:** demo: differential PASS + benchmark (4,5–10,3× już na specyfikacji) + bramka z exit-code w CI. ✅

### Faza 1 — Szkielet pipeline'u (tydz. 2–4) ⏱ 3 tydz. — w toku (2026-08-24)
- [x] Scaffold repo (struktura z §3), CI (cargo + pytest) — **workflow gotowy; push
      wstrzymany: token GitHub App bez uprawnienia `workflows`** (do wyjaśnienia z Arena).
- [x] Tracer v1: profil + typy + harvest argumentów → manifest — **ZAMROŻONY
      `hotport.manifest/0.1.0`** (semver: opcjonalne pole=minor, zmiana=major).
      Detekcja mutacji K4, frakcja ASCII (ADR-0005), próbki replay z dedup/cap.
- [x] Wrapper PyO3 z przełącznikiem `HOTPORT_IMPL=python|rust|both` (canary) —
      zrealizowany już w fazie 0 (shim `hotport_spike`).
- [x] Silnik L1 (replay) + porównywarka wyników + exit-code gate — done w fazie 0;
      w fazie 1 rozszerzony o warstwę **l1-trace** (manifest→runner): 1784 PASS.
- **DoD:** `pyaccel verify examples/targets/validators` z REALNYM .so z CI —
  **SPEŁNIONE 2026-08-24 (commit 82400c3): pierwszy w pełni zielony przebieg CI**:
  fmt → testy workspace → build (core+PyO3) → płaski artefakt .so → suite vendora
  → differential na prawdziwym Rust → bramka (exit-code) → benchmark → raporty.
  Droga wymagała naprawy 7 bugów (REPORT.md) — każdy złapany przez inną warstwę
  pipeline'u, co samo w sobie waliduje architekturę „wielu siatek".

### Faza 2 — Translator v1 (tydz. 5–7) ⏱ 3 tydz. — w toku (v0 done, 2026-08-24)
- [x] Rdzeń deterministyczny **v0** (hotport_trans, prototyp pythonowy z regułami
      1:1 dla Rust i cienia): 5/5 funkcji celu automatycznie, golden `.rs`
      commitowane, differential 654/0, K3-routing zademonstrowany (84/133 w
      safe_mul). Reguły v0: koercja literału ≤2^53, brak truthiness/`//`/`%`/`**`/try,
      `len→chars().count()`, checked_add/sub/mul.
- [x] CI pełne zielone (2026-08-24, run 82400c3): 895+27 testów, bramka rust
      1743 PASS, **benchmark DoD spełniony: 4,52×/6,77×/8,46× przez ctypes**
      (uuid jako jedyny gorszy od pythonowej specyfikacji — podatek FFI+alokacje;
      potwierdzenie strategii klastrów + PyO3).
- [ ] Podpięcie generated/*.rs do kompilacji w CI + repair loop rustc;
      przeniesienie reguł v0 do crate hotport-trans; upgrade pyo3 (0.23.5 → 0.29).
- [x] L2 property-based z seedami — rozszerzone o cele translatora (granice i64,
      NaN/inf, unicode, stratyfikacja krawędzi mnożenia).
- **DoD:** ≥ 5 funkcji z `validators` przełożonych automatycznie, bramka L1+L2 zielona, benchmark ≥ ×2 na min. 3 z nich.

### Faza 3 — Głębokość weryfikacji i raport (tydz. 8–9) ⏱ 2 tyg.
- [ ] K3 (overflow), K5 (wyjątki), K6 (edge-seeds), K8 (kolejność) w pełni wymuszone.
- [ ] L3: fuzzing (mutacja stringów) dla funkcji parsujących — demo na `dateutil`/`slugify`.
- [ ] Benchmark harness + raport końcowy (Markdown/HTML): tabela funkcja × speedup × status × dowody.
- **DoD:** pełny raport dla 2 bibliotek celów; raport z flagami czerwonymi też wygląda dobrze (zaufanie > pokazuch).

### Faza 4 — Pilot publiczny (tydz. 10–11) ⏱ 2 tyg.
- [ ] Trzeci cel end-to-end (`dateutil`-parser albo pierwsza **prawdziwa biblioteka community** — issue/PR do maintainera z raportem).
- [ ] Dokumentacja: quickstart, kontrakty, ograniczenia (szczególnie lista pułapek — to buduje wiarygodność).
- [ ] Launch: post „jak przyspieszyliśmy X ×N z dowodem równoważności" (blog + HN/Reddit r/rust, r/Python — ton: narzędzie do przyspieszania, nie „Rust better").
- **DoD:** 1 realny użytkownik spoza projektu przebiega quickstart end-to-end bez naszej pomocy.

### Faza 5 — Produktyzacja (tydz. 12+) — priorytety wg feedbacku
- mutowalne argumenty (K4) · klasy/metody · generatory · `async` · GitHub Action „pyaccel gate" · cache tłumaczeń · tryb `both` (kanarek produkcyjny) na poważnie · obsługa `numpy` (data plane)

---

## 7. Ryzyka i mitygacje

| # | Ryzyko | Prawdopodobieństwo | Mitygacja |
|---|--------|--------------------|-----------|
| R1 | Różnice semantyczne prześlizgną się do produkcji | średnie | Z5 (deny by default), L1+L2 obowiązkowe, rejestr pułapek §4.4, tryb `both` jako kanarek |
| R2 | Koszt FFI zjada zysk (małe/frekwentne wywołania) | wysokie | bramka wydajności (×1.5) przed promocją; tłumaczenie **całych klastrów** call-graph (1 przejście przez granicę zamiast 20); bufferowane konwersje |
| R3 | LLM niedeterministyczny / kosztowny / nie chce firm chmury | średnie | LLM opcjonalny (Z6), temperature 0 + cache, ścieżka deterministyczna zawsze działa |
| R4 | Inferencja typów zawodzi (dynamiczny Python) | wysokie | wymóg w MVP: typy obserwowane z tracerem; brak typu → poza zakresem (Z5); MonkeyType-style z wielu uruchomień |
| R5 | `re`/`datetime`/`json` — niemożliwa w 100% zgodność | pewne | tabela różnic per API; fallback „prześlij przez granicę do Pythona" (bezpieczniejsze, wolniejsze) jako legalny wynik translacji |
| R6 | Utrzymanie wielu wersji Pythona | średnie | `abi3` wheels, testy na macierzy 3.9–3.13 |
| R7 | Konkurencja (py2many, depyler) ruszy w to samo | średnie | nasza przewaga = weryfikacja+raport+canary (oni tego nie mają); tempo: faza 4 ≤ 11 tyg. |

---

## 8. Metryki sukcesu (KPI)

- **% funkcji auto-zweryfikowanych** (cel fazy 4: ≥ 60% kandydatów w celach demonstracyjnych),
- **mediana speedupu** na promowanych funkcjach (cel: ≥ ×3; dla parserów ≥ ×10),
- **czas od `init` do raportu** dla nowej, mieszczącej się w zakresie biblioteki (cel: < 30 min),
- **false-alarm rate** bramki (różnice, które są błędami harnessu, nie kodu — cel: < 5%; każdy analizujemy),
- adopcja: github stars / issue od obcych / 1 merged PR do biblioteki community.

---

## 9. Różnicowanie (dla dokumentu publicznego)

| | py2many | depyler | **pyaccel** |
|---|---|---|---|
| Cel | ogólny transpiler (wiele języków) | annotated Python → Rust | **hot-library → Rust z dowodem** |
| API 1:1 | ✗ | częściowo | ✓ (Z1) |
| Weryfikacja równoważności | ✗ | property-based (ograniczone) | ✓ L1+L2+L3, artefakt w CI |
| Benchmark/raport | ✗ | ✗ | ✓ (Z7) |
| Kanarek produkcyjny (`both`) | ✗ | ✗ | ✓ (Z4) |
| Profil/gorące ścieżki | ✗ | ✗ | ✓ |

---

## 10. Otwarte decyzje (do ADR)

1. **Nazwa** — propozycje: `pyaccel`, `hotport`, `rustport` (sprawdzić dostępność).
2. **Licencja** — Apache-2.0 (patent grant) vs MIT; cele demonstracyjne tylko jako vendor w `examples/` z zachowaniem licencji.
3. **Parser**: tree-sitter-python vs rustpython-parser (spike w fazie 0).
4. **LLM**: czy w ogóle w v1, czy dopiero v2 (rekomendacja: v2 — najpierw deterministycznie, LLM jako plugin).
5. **Monetyzacja** (nie blokuje MVP): OSS core + płatne: tryb `both`-as-a-service dla enterprise, wsparcie wdrożeń, chmurowy runner weryfikacji.

---

## 11. Pierwsze kroki — checklist na jutro — **WYKONANA 2026-08-24**

- [x] Struktura repo (workspace Cargo `crates/hotport-*` + `examples/spike/` + vendored target; `py/` z §3 zamienione na `examples/spike/python` — tracer trafi tam w fazie 1).
- [x] ADR-0001 (nazwa `hotport` + Apache-2.0), ADR-0002 (parser — PROPOSED), ADR-0003 (LLM off w v1), ADR-0004 (sieć sandboxa → std-only + CI-first), ADR-0005 (kontrakt ASCII + routing per-input).
- [x] Vendor `validators` 0.35.0 (commit 70de324) → `examples/targets/validators/` + suite w CI (895 passed) + VENDOR.md.
- [x] Ręczny port **3 funkcji** (slug/uuid/ipv4) + differential + bramka + bench → patrz REPORT.md.
