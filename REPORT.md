# REPORT — Faza 0: spike walidacyjny (2026-08-24)

> Cel fazy (PLAN.md §Faza 0): **udowodnić, nie założyć** — ręczny port 3 funkcji
> biblioteki `validators` 0.35.0 na Rust + silnik differential z bramką.
> Odpowiedź na pytanie „czy to w ogóle da się zrobić" brzmi: **tak, i harness
> łapie prawdziwe bugi — w tym cztery moje własne.**

## Streszczenie w liczbach

| Miara | Wynik |
|---|---|
| Przypadki differential (L1 replay + L2 seedowane, seed=42) | **1743** |
| Rozbieżności ref-spec vs oryginał Pythona | **0** (PASS ✅) |
| Pokryte rdzeniem (po routing) | 1670 (uuid 499/539, ipv4 645/678, slug 526/526) |
| Routing per-wejście (kontrakt ASCII, ADR-0005) | 73 — wszystkie uzasadnione |
| Wstrzyknięte bugi wyłapane przez bramkę | **5/5** |
| Testy pytest spike'a | 13 passed, 1 skipped (backend `rust` — wymaga .so, odpala się w CI) |
| Pełna suite vendora (sanity) | **895 passed** |
| Czułość parzystości API | 3 tryby shimu × 1743 przypadki — identyczne wyniki, w tym wycieki wyjątków |

Benchmark (median ns/op, wejścia z generatora L2):

| fn | python (validators) | ref (spec w Pythonie) | py/ref |
|---|---|---|---|
| slug | 5418 | 1197 | 4.52× |
| uuid | 5529 | 1059 | 5.22× |
| ipv4 | 15928 | 1542 | 10.33× |

**Uczciwa interpretacja:** kolumna `ref` to wciąż Python (bez `re`/`ipaddress`/
`uuid`/dekoratora) — 4–10× zysku **nie wymaga w ogóle Rusta**, to efekt omijania
ciężkiej machinerii stdlib. Kolumna `rust` (ctypes, w CI) będzie zawierać podatek
FFI ~0,3–1 µs — dla tych mikro-funkcji może zjeść cały zysk (ryzyko R2 z PLAN.md).
Potwierdza to tezę architektoniczną: tłumaczyć **klastry** (jedno przejście przez
granicę FFI), nie pojedyncze liście, i celować w PyO3.

## Ograniczenie środowiska (ADR-0004)

Sandbox dev nie ma sieci do crates.io / static.rust-lang.org / GitHub Releases
→ brak toolchaina Rusta lokalnie. W konsekwencji:

* kod Rust jest **kompletny** (rdzeń std-only + FFI + binding PyO3) i kompiluje/
  testuje się w **CI** (workflow `ci.yml`: fmt, testy, build, artefakt `.so`
  zasilający differential w jobie Pythona),
* poprawność **logiki** jest mimo to udowodniona już dziś: backend `ref` to
  linia-po-linii wykonywalna specyfikacja rdzenia Rust, zweryfikowana
  differentialowo wobec oryginału na 1743 przypadkach.

## Złote reguły — pułapki wykryte empirycznie (probe-first, nie z dokumentacji)

Wszystkie potwierdzone na Pythonie 3.11 przed napisaniem jakiejkolwiek linii Rusta:

| # | Zachowanie oryginału | Konsekwencja dla portu |
|---|---|---|
| G1 | `slug("abc\n")` → **True** (`$` w `re` dopasowuje przed JEDNYM końcowym `\n`) | obetnij max 1 końcowy `\n` przed automatem |
| G2 | `uuid`: `'uuid:'` działa **bez** `'urn:'`, replace jest **wszędzie** w stringu, tylko małymi literami (`URN:UUID:` → invalid) | replace-anywhere, case-sensitive, w kolejności urn→uuid |
| G3 | `uuid`: `strip("{}")` to zbiór znaków na końcach (nie prefiks/sufiks), dowolna liczba | `trim_matches` z predykatem `{`/`}` |
| G4 | `uuid`: `'+2bc1…ec9f'` (plus + 31 hex) → **VALID** — `int()` przyjmuje znak | gramatyka `+?` przed hexami |
| G5 | `uuid`: podkreślniki PEP 515 między hexami → **VALID** | pojedyncze `_` między cyframi |
| G6 | `uuid`: 30 hexów + 2 spacje/tabulator/`\x0b` → **VALID** — `int()` obcina białe znaki (zbiór: spacja, `\t`, `\n`, `\r`, `\x0b`, `\x0c` — **szerszy niż Rust `is_ascii_whitespace`!**) | jawny zbiór trimowanych znaków, nie helper |
| G7 | `uuid`: arabskie `٢` zamiast cyfry → **VALID** (unicode Nd w `int()`) | **poza kontraktem ASCII** → routing (ADR-0005) |
| G8 | `uuid`: `'-' + kanoniczny_z_myślnikami` → **VALID** (`replace('-','')` usuwa też znak liczby!), ale `'-' + 31hex` → invalid (zostaje 31) | usuwaj wszystkie `-` przed checkiem długości; „ujemne UUID" nie istnieją |
| G9 | `ipv4`: oktet `'01'` → invalid, ale prefix `'/024'` → **VALID** (asymetria ipaddress!) | osobne reguły parsera oktetu i prefiksu |
| G10 | `ipv4`: maska kropkowana musi być ciągła (`255.0.255.0` invalid), a jej oktety też bez zer wiodących (`255.255.255.00` invalid) | walidacja maski przez sprawdzanie ciągłości |
| G11 | `ipv4`: `'/+24'`, `'/ 24'`, `'/٣٢'` → invalid (isascii+isdigit **przed** `int()`) | whitelist cyfr ASCII w prefiksie |
| G12 | `validators.uuid(123)` → **AttributeError wycieka** przez dekorator (łapie tylko ValueError/TypeError/UnicodeError) | parzystość API przez routing nie-str do oryginału + reużycie ich dekoratora |
| G13 | falsy-guard: `uuid(0)`, `slug(None)`, `ipv4('')` → ValidationError (nie wyjątek) | zachowane automatycznie przez reużycie `@validator` |

## Bugi znalezione przez harness W TRAKCIE spike'a (dowód czułości)

1. **Mój automat slugu** przyjmował wiodujący `'-'` (inicjalny stan flagi) —
   differential [L2] to wyłapał na `-fz3zfk-…` (py=false, core=true).
2. **Moja gramatyka uuid** odrzucała cyfrę po podkreślniku (błędny stan po `_`).
3. **Moja teoria „ujemnego UUID"** była błędna (patrz G8) — harness pokazał,
   że `'-'+kanoniczny` jest VALID, zanim zdążyłem wprowadzić ją do rdzenia.
4. **Brak trimowania białych znaków** w pierwszej wersji gramatyki (G6).
5. Celowo **wstrzyknięte bugi** (5 scenariuszy: wiodący `-` w slugu; pominięte
   usuwanie myślników w uuid; odrzucenie PEP 515; zera wiodące w oktetach;
   odrzucenie `/024`) — **wszystkie oflagowane**, każdy na właściwym przypadku.

## Wnioski architektoniczne (przenoszone do fazy 1)

1. **Routing per-WEJŚCIE** (ADR-0005) sprawdza się w praktyce: 73/1743 wywołań
   poszło do oryginału (głównie unicode z mutacji L2), a funkcje i tak są
   „promowalne" — kontrakt zamiast rezygnacji z funkcji.
2. **Reużycie dekoratora `@validator`** w shimie = parzystość API (Z1) z definicji:
   identyczne `ValidationError`, identyczne wycieki wyjątków, identyczny env
   `RAISE_VALIDATION_ERROR`. Zero hand-rolled parzystości.
3. **Wykonywalna specyfikacja (`ref`) przed Rustem** to tania opcja wyjścia
   (executable spec) — pisz port dopiero, gdy spec przejdzie differential.
4. **Probe-first**: żadnej reguły nie zakładamy z dokumentacji — wszystko
   empirycznie wobec prawdziwego interpretera (to zalążek przyszłego tracera
   kontraktów L2 z PLAN.md).
5. **Bramka ma exit-code** — od dziś nadaje się do CI (workflow podpięty).

## Faza 1 — tracer v1 + zamknięcie pętli (2026-08-24, sesja 2)

**Nowy komponent:** `examples/spike/python/hotport_tracer/` (PLAN.md §3 [1]).

* Wrapuje funkcje biblioteki-celu i rejestruje: liczniki, czas własny (ns),
  **kształty typów** argumentów/wyników (`list[int|str]`, `dict[str->int]`,
  `uuid.UUID`…), zaobserwowane wyjątki, **detekcję mutacji kontenerów** (K4,
  snapshoty repr przed/po), **frakcję ASCII** argumentów (ADR-0005) oraz
  **próbki replay** prawdziwych argumentów (dedup + capy + redakcja rozmiaru).
* **Manifest ZAMROŻONY: `hotport.manifest/0.1.0`** (reguły semver w nagłówku
  `manifest.py`: nowe pole opcjonalne = minor; zmiana semantyki = major).
* CLI: `python -m hotport_tracer --module validators --names slug uuid ipv4
  --pytest <suite> --out manifest-validators.json` → artefakt commitowany.

**Pętla zamknięta (test integracyjny + runner):**

```
suite vendora ──(tracer)──► manifest-validators.json ──(replay)──► differential ──► bramka
```

* Wynik na prawdziwych danych: ipv4 45 wywołań/25 próbek, slug 8/8, uuid 8/8,
  **ascii_fraction = 1.0** (żadne prawdziwe wywołanie nie wymagało routingu —
  koszt kontraktu ASCII w praktyce ≈ 0),
* runner `--manifest`: **+41 przypadków l1-trace**, łącznie **1784 przypadki,
  PASS ✅, 0 rozbieżności**,
* testy: 17 passed (tracer: kształty, K4, dedup, roundtrip manifestu,
  integracja end-to-end; 1 skip = backend `rust` czeka na .so z CI).

## Faza 2 — translator deterministyczny v0 (2026-08-24, sesja 3)

**Nowe komponenty:** `examples/spike/python/hotport_trans/` (translator v0),
`examples/targets/demo_fns.py` (syntetyczny moduł-cel), `examples/spike/generated/`
(golden: `.rs` + cień — commitowane artefakty), runner uogólniony (rejestr celów,
etykiety wyników `int:/float:/str:`, przypadki wieloargumentowe).

**Podejście podwójnej siatki bezpieczeństwa** (rozszerzenie metodologii ref z fazy 0):
translator emituje RÓWNOCZEŚNIE (1) kod Rust (tekst — kompilacja w CI) i
(2) **cień** — Python z guardami semantyki Rust (koercja `float()` = `as f64`,
`_bin` z kontrolą i64 = `checked_*`). Cień differentialowo weryfikujemy wobec
oryginału już dziś; golden-testy blokują drift reguł.

**Wynik: 5/5 funkcji przetłumaczonych automatycznie** (in_band, grade, sum_upto,
code_ok, safe_mul), differential **654 przypadki / 0 rozbieżności**, w tym:
* `safe_mul`: **84/133 wywołania routowane** na krawędziach i64 (K3 żyje:
  `2^62×2 → None` = routing, `-(2^63)×1` = OK, `2^63×1` = routing argumentu),
* NaN/±inf w grade/in_band zgodne, `len(unicode)` = punkty kodowe = `chars().count()`.

**Bugi znalezione po drodze (4 — wszystkie udokumentowane w testach):**
1. **AST `Mult` ≠ „Mul"** — mapa operatorów miała złą nazwę węzła (safe_mul
   „nieobsługiwany") — klasyczny błąd nazewnictwa ast.
2. **`let` zamiast przypisania w pętli** (`total = total + i` emitował `let mut
   total = ...` → shadowing, funkcja zawsze zwracałaby 0). **Cień tego NIE
   wyłapał** (Python nie ma deklaracji) — dowód, że potrzebne są DWA nety:
   cień (błędy reguł) + golden/kompilacja (błędy emitera tekstu Rust).
3. **`.startswith` nie istnieje w Rust** (`starts_with`) — mapowanie nazw metod.
4. Wcięcie guardów i64 w generowanym cieniu (SyntaxError przy exec).

**Pierwszy przebieg CI (pierwsza kompilacja!) złapał kolejne 4:**
trzy błędy kompilacji (domknięcie przenoszone przed użyciem w hotport-verify;
`&String` vs `&str` w format! w hotport-bench; prywatny konstruktor `Utf8Error`
w ffi.rs) oraz **błędne oczekiwanie w złotej regule ipv4**: `1.1.1.1/00` JEST
poprawne (`int('00')=0`) — rdzeń Rust zwrócił słusznie `Some(true)`, a mój test
wymagał `Some(false)`, bo odczytałem probe z `strict=True` (tam zawiniły bity
hosta, nie maska). Lekcja-żelazo: oczekiwanie testu wyprowadzamy wyłącznie z
probe'u o dokładnie tych parametrach, których używa kod.

**Bug piąty — najcenniejszy (semantyczny, w rdzeniu Rust, złapany przez test
jednostkowy w CI):** w `ipv4_core` operator `?` na `parse_dotted(addr_s)?` /
`parse_netmask(m)?` propagował `None` **poza funkcję** — a `None` znaczy w
umowie rdzenia „poza kontraktem ASCII → routing do Pythona", nie „wartość
niepoprawna"! `'0127.0.0.1'` zwracało `None` zamiast `Some(false)`. Ref-backend
(Python, `if addr is None: return False`) był poprawny — dlatego differential
na cieniu przechodził, a ten bug mógł zjeść dopiero **skompilowany** test
jednostkowy Rusta w CI. Puenta dla architektury: cień nie widzi bugów
idiosynkratycznych dla Rusta (`?`/ownership) — dwa nety (cień + kompilacja/testy
Rust w CI) to nie opcja, to konieczność. Poprawka: jawne `match` zamiast `?`
na granicy „parser → werdykt".

**Bug szósty (warstwa transportowa, tylko na prawdziwym .so w CI):**
`rust_backend` dla nie-stringów robił `bool(None)` → `False` zamiast `None`
(= routing). Objawy trzy: `uuid(UUID(...))` → false (miało być true),
`uuid(123)` → false (miało być raise:AttributeError), tryb kanarkowy `both`
słusznie rzucał `CanaryMismatch`. Ref-backend i logika Rust były poprawne —
błąd siedział wyłącznie w kleju ctypes, którego **nie dało się zobaczyć bez
skompilowanego .so** (lokalnie test był skipowany). Dodany test regresyjny ze
stubem FFI łapie tę klasę błędów także bez Rusta. Dokładnie tego celu służy
strategia CI-first z ADR-0004.

**Reguły semantyczne v0 (zapisane w kodzie i testach):**
* mixed int/float porównania: DOZWOLONE tylko dla literału int ≤2^53 (dokładnie
  reprezentowalny w f64; python porównuje wartościowo — koercja zmiennych
  odrzucona, bo gubi precyzję ≥2^53 — pułapka K2),
* cień symuluje `as f64` przez `float()` — różnica vs dokładny oracle na wielkich
  intach WYJDZIE w differentialu (świadomie, zamiast cichego przekłamania),
* brak truthiness (`if s:` → odrzucone), `//`, `%`, `**`, try/except — poza v0,
* pułapka wydajności differentialu: oracle z pętlą O(n) nie może dostawać
  granicznych n (zawiesza suitę) — granice K3 testujemy na funkcjach O(1).

**Regresja fazy 1:** 1784 przypadki PASS (manifest l1-trace) — nic nie pękło.

## Kamień milowy: pierwszy w pełni zielony CI (2026-08-24, commit 82400c3)

Pipeline działa END-TO-END: push → fmt (zielony) → `cargo test --workspace` →
build rdzenia i PyO3 → płaski artefakt `.so` → pełna suite vendora (895) →
pytest spike'a **z prawdziwym backendem rust** (koniec skipów) → bramka
`--backend rust` (exit-code) → benchmark z kolumną py/rust → artefakt raportów.

Droga do zieleni = 7 naprawionych bugów, każdy wykryty przez INNĄ warstwę:

| # | Bug | Wykryła warstwa |
|---|-----|-----------------|
| 1–3 | trzy błędy kompilacji (closure-move, format! typy, prywatny Utf8Error) | pierwsza kompilacja (CI, cargo) |
| 4 | złe oczekiwanie testu `/00` (probe ze złymi parametrami) | test jednostkowy Rusta (CI) |
| 5 | operator `?` = routing zamiast invalid w ipv4_core | test jednostkowy Rusta (CI) |
| 6 | `bool(None)`→False dla nie-stringów w kleju ctypes | differential na .so + kanarek `both` (CI) |
| 7 | sys.path katalog-pakietu zamiast rodzica | krok bramki w CI (środowisko bez PYTHONPATH) |

Do uzupełnienia → **UZUPEŁNIONE (pełne logi runa 82400c3, oba joby zielone):**

* suite vendora: **895 passed**; pytest spike'a: **27 passed, 0 skipped**
  (differential na prawdziwym `.so` wystartował — koniec ery skipów),
* bramka: `backend=rust 1743 przypadki, verdict=PASS ✅`
  (ipv4 645 porównanych/33 routed, slug 526/0, uuid 499/40 — 0 rozbieżności),
* **benchmark (median ns/op, GH runner, rustc 1.98, pyo3 0.23.5):**

| fn | python (validators) | ref (spec, py) | **rust (ctypes)** | py/ref | **py/rust** |
|---|---|---|---|---|---|
| slug | 4161 | 1045 | **615** | 3.98× | **6.77×** |
| uuid | 4105 | 877 | **909** | 4.68× | **4.52×** |
| ipv4 | 10105 | 1290 | **1195** | 7.83× | **8.46×** |

**Analiza (R2 w liczbach):** nawet przez ctypes (podatek FFI rzędu 0,4–1 µs
na wywołanie — widać go jako różnicę rust vs ref, bo czysty rdzeń liczy
~100–300 ns) port daje **4,5–8,5×**. Ciekawostka: `uuid` jest jedynym
przypadkiem, gdzie ctypes-Rust (909) przegrywa z pythonową specyfikacją (877)
— koszt FFI + alokacje w transformacjach stringów zjadł przewagę rdzenia;
mimo to pozostaje 4,5× szybszy od oryginału. Wniosek strategiczny potwierdzony:
**docelowa architektura = PyO3 + tłumaczenie całych klastrów** (jedno przejście
przez granicę na łańcuch wywołań, nie na liść), bo wtedy podatek FFI znika
ze statystyki per-wywołanie. DoD fazy 2 (benchmark ≥×2 na min. 3 funkcjach):
**spełnione 4,52×/6,77×/8,46×**.

## Faza 2.1 — KLASTRY [REVIEW pkt 8-9] (2026-08-25)

Odpowiedź kodem na rekomendację „portuj hot REGION, nie hot function"
(umotywowana benchem: uuid przez ctypes przegrał z pythonową specyfikacją).

* **tracer**: call-graph (`callers` w manifeście — **schema 0.2.0**, pole
  opcjonalne = minor) + `clusters_from_manifest()` — automatyczne odkrywanie
  klastrów ze śladu (entry = funkcja wołana tylko z zewnątrz).
* **translator v0.2**: `translate_cluster(source, entry)` — wywołania
  międzyfunkcyjne w podzbiorze v0; entry jako `pub fn`, wnętrza prywatne
  (wywołania wewnętrzne w Rust darmowe, **FFI płaci się raz**); `?` na
  wywołaniach lustrzane z `_call` w cieniu. CLI: `--entry <nazwa>`.
* **rig**: `demo_cluster.py` (admission → in_band/is_score_valid → grade),
  wykryty automatycznie ze śladu (4 członków). Golden: cluster_admission.rs +
  cross-check z core/src/cluster.rs.
* **bench 3-wariantowy**: python-łańcuch · rust-LIŚCIE (2×FFI — patologia)
  · rust-KLASTER (1×FFI) — liczby z CI.
* Uczciwe zastrzeżenie: rig jest trywialny (logika float) — możliwy werdykt
  NOT-WORTH nawet dla 1×FFI, i to też jest wartościowa informacja.

## Kamień milowy 2: klastry zielone w CI (2026-08-25, run a37055d)

Pełny sukces po fixie #8 (wnętrza klastra `pub(crate)` — E0603 wykryte przez
adnotacje publicznego API bez czytania logów). Wszystkie kroki zielone, w tym:
differential klastra na prawdziwym `.so` (koniec skipów), bramka, bench
3-wariantowy. Liczby klastra (python vs 2×FFI vs 1×FFI): patrz
`examples/spike/report/bench.md` z bot-commita / artefakt.

Przy okazji: infrastruktura odczytu wyników — runy/kroki/adnotacje czytane
z publicznego API; logi/artefakty (blob Azure) nadal poza allowlistą proxy
sandboxa → stąd bot-commit raportów do repo (docs/ci-workflow.yml).

## Co dalej (Faza 2 — pozostało)

- [ ] Pierwszy przebieg CI: kompilacja+testy Rusta, artefakt `.so`, differential
      na backendie `rust` (odznaczyć skip w sandboxie) i kolumna py/rust w benchu,
- [ ] Tracer v1 (profil + typy + harvest argumentów → `manifest.json`),
- [ ] Zamrożenie formatu manifestu (semver) + serde w CI,
- [ ] Rozszerzenie zestawu L2 o mutacje strukturalne (fuzzing L3 dla parserów),
- [ ] Drugi cel demonstracyjny (`python-slugify`).

## Odtworzenie wyników

```bash
pip install pytest "eth-hash[pycryptodome]"
python -m pytest examples/spike -q                       # 17 passed (1 skipped bez .so)
python examples/spike/python/hotport_spike/runner.py --backend ref    # bramka PASS
PYTHONPATH=examples/spike/python:examples/targets/validators/src \
  python -m hotport_tracer --module validators --names slug uuid ipv4 \
  --pytest examples/targets/validators/tests/test_slug.py \
             examples/targets/validators/tests/test_uuid.py \
             examples/targets/validators/tests/test_ip_address.py \
  --out examples/spike/manifest-validators.json           # ślad → manifest
python examples/spike/python/hotport_spike/runner.py --backend ref \
  --manifest examples/spike/manifest-validators.json      # pętla zamknięta (1784 PASS)
python examples/spike/python/hotport_spike/bench.py
PYTHONPATH=examples/targets/validators/src \
  python -m pytest examples/targets/validators/tests -q                # 895 passed
```
