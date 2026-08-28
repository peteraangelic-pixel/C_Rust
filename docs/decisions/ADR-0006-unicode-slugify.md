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
   L2 (diakrytyki, CJK, emoji, znaki composed vs decomposed — NFC/NFD
   to pułapka K2-klasyczna: normalization przed porównaniem!).

## Alternatywy odrzucone

* Pełny port unidecode (tysiące mapowań) — koszt >> zysk na v1.
* Rozszerzenie kontraktu ASCII o „cały Unicode w core" — psuje std-only rdzenia.

## Metryka sukcesu

`ascii_fraction` przestaje być metryką routing-u; nowa metryka: **ułamek
wejść obsłużonych przez rdzeń** (cel ≥ 0.9 na suite slugify) + speedup
≥ ×3 na promowanych funkcjach (NFD/NFC w raporcie jako osobny wiersz K2).
