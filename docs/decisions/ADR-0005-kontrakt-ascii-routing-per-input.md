# ADR-0005: Kontrakt ASCII i routing per-WEJŚCIE (nie per-funkcja)

* Status: ACCEPTED (2026-08-24, z doświadczeń fazy 0)

## Kontekst

Probe'y semantyczne (REPORT.md §„złote reguły") pokazały, że Python akceptuje
wejścia, których wierna replikacja w Rust std jest nieproporcjonalnie droga:

* `int(x, 16)` w `uuid.UUID` akceptuje **cyfry Unicode Nd** (np. arabskie `٢`)
  — bo CPython transformuje unicode digits przed parsowaniem,
* `int()` obciąga też **unicode whitespace** (`\x85`, `\xa0`),
* `$` w `re` dopasowuje przed końcowym `'\n'` (to replikowalne — zrobione),
* `int()` przyjmuje `+` i `_` (PEP 515) — replikowalne, zrobione.

## Decyzja

1. **Kontrakt rdzenia = ASCII**: `uuid_core`/`ipv4_core` zwracają `None` dla
   wejść nie-ASCII. `None` oznacza: *wywołujący MUSI skierować to konkretne
   wywołanie do oryginału Pythona*.
2. **Routing jest per-wejście, nie per-funkcja** — shim (`hotport_spike/__init__.py`)
   decyduje o każdym wywołaniu osobno. Funkcja nigdy nie „nie kwalifikuje się"
   przez egzotyczne wejścia; traci tylko te konkretne wywołania.
3. Silnik differential oznacza takie wywołania jako `routed` i osobno sprawdza,
   czy routing jest **uzasadniony** (nie-str albo nie-ASCII) — nieuzasadniony
   routing to błąd bramki.

## Uzasadnienie

* Z5 („deny, nie zgaduj") w praktyce: nie replikujemy bug-for-bug niereprezentowalnej
  luźności — deklarujemy granicę i ją egzekwujemy.
* Koszt: wywołania nie-ASCII trafiają na wolną ścieżkę. W praktyce (validation
  library) to promile; profiler pokaże, jeśli nie.
* Unicode Nd tablice wchodzą do wersji produkcyjnej (crate UCD) — wtedy kontrakt
  się rozszerza, a bramka udowodni równoważność na tych wejściach.

## Konsekwencje

* Raport differential pokuje `routed` osobno (widoczny „dispatch tax").
* Dla funkcji IO/typów dynamicznych analogiczna zasada: kontrakt → rdzeń,
  poza kontrakt → oryginał.
