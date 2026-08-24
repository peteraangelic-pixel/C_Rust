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
