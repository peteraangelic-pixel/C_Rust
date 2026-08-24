# ADR-0002: Frontend parsera Pythona (AST)

* Status: PROPOSED — decyzja po spike'e fazy 1 (PLAN.md Faza 0/1)

## Kontekst

Translator potrzebuje AST Pythona po stronie Rusta. Sandbox dev nie ma dostępu
do crates.io (ADR-0004), więc faza 0 obywa się bez parsera (rdzenie pisane ręcznie).

## Opcje

| | tree-sitter-python | rustpython-parser |
|---|---|---|
| Dojrzałość | wysoka (Neovim/GitHub) | dobra |
| AST | konkretne, z błędami składni | pełne, wierne CPythonowi |
| Integracja | bindings C, generation | czysty Rust |
| Błędy składniowe kodu | tolerancyjny (dobrze dla legacy) | błąd kompilacji |

## Analiza

Błędy składniowe w kodzie klienta to realny scenariusz (legacy!) — przemawia za
tree-sitter. Pełne, wierne CPythonowi typy AST przemawiają za rustpython.

## Plan

Spike porównawczy w Fazie 1 na plikach vendora (parsers: pełny plik → AST → dump
+ testy regresji na 100 plikach z `examples/targets`). Kryteria: pokrycie
składni, ergonomia typów, czas budowy. Do tego czasu: bez decyzji.
