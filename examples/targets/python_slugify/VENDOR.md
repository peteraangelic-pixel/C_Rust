# Vendor: python-slugify (commit 7b6d5d9, MIT)

* Źródło: https://github.com/un33k/python-slugify
* Vendor: `slugify/` + `test.py` + `LICENSE` + `README.md` + `pyproject.toml`
* Zależność runtime: `unidecode` (`pip install unidecode`)
* Suite: `PYTHONPATH=. python -m pytest test.py -q` → **82 passed** (2026-08-24)

## Dlaczego (cel demonstracyjny #2, PLAN.md §2)

* czysty Python, dobra suite, *string-first* — naturalny partner differentialu,
* **wyzwanie Unicode**: ślad tracera na własnej suite biblioteki daje
  `ascii_fraction = 0.593` (105 wywołań slugify, 25 próbek replay) — 40% wejść
  poza kontraktem ASCII z ADR-0005. To wymusza decyzję projektową fazy 2:
  (a) tabela PRE_TRANSLATIONS jako dane + unicode lowercase w rdzeniu Rust
  (crate `unicode-normalization`), albo (b) routing — ale wtedy tracimy „hot".
* manifest: `examples/spike/manifest-slugify.json` (schema 0.1.0).

## Nie modyfikujemy kodu vendora
