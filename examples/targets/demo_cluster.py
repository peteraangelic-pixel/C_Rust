"""Cel demonstracyjny: KLASTER (lancuch wywolan) — jedno przejscie FFI.

[REVIEW pkt 8-9, potwierdzone benchem CI: uuid przez ctypes byl wolniejszy
niz pythonowa specyfikacja rdzenia — podatek FFI per wywolanie]. Portujemy
hot REGION (admission -> in_band/grade/is_score_valid), nie pojedyncze liscie.
"""


def grade(points: float) -> int:
    """Punktowy prog -> ocena."""
    if points >= 90:
        return 5
    elif points >= 75:
        return 4
    elif points >= 60:
        return 3
    else:
        return 0


def in_band(value: float, lo: float, hi: float) -> bool:
    return lo <= value and value <= hi


def is_score_valid(points: float) -> bool:
    band = grade(points)
    return band >= 3 and band <= 5


def admission(points: float, lo: float, hi: float) -> bool:
    in_range = in_band(points, lo, hi)
    score_ok = is_score_valid(points)
    return in_range and score_ok
