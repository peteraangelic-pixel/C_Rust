# WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
# Cień = te same reguły translacji co kod Rust, wykonywalne w Pythonie:
# * int: arytmetyka _bin z kontrolą zakresu i64 (K3) — przekroczenie → _Out → None (routing),
# * brak truthiness — warunki jawnie bool,
_I64_MIN = -9223372036854775808
_I64_MAX = 9223372036854775807


class _Out(Exception):
    pass


def _chk(r):
    if not (_I64_MIN <= r <= _I64_MAX):
        raise _Out()
    return r


def _bin(op, a, b):
    if op == 'a':
        return _chk(a + b)
    if op == 's':
        return _chk(a - b)
    if op == 'm':
        return _chk(a * b)
    raise AssertionError(op)


def _floordiv(a, b):
    # python: floor + ZeroDivisionError; cien: b==0 -> _Out (routing, jak '?' w rust)
    if b == 0:
        raise _Out()
    return _chk(a // b)


def _pymod(a, b):
    if b == 0:
        raise _Out()
    return _chk(a % b)


def _neg(a):
    return _chk(-a)


def _call(f, *args):
    # wywołanie wewnętrzne (v0.2 klastry): None z wnętrza = _Out —
    # lustrzane odbicie operatora `?` w generowanym rust
    r = f(*args)
    if r is None:
        raise _Out()
    return r

def admission(points, lo, hi):
    try:
        in_range = _call(in_band, points, lo, hi);
        score_ok = _call(is_score_valid, points);
        return (in_range) and (score_ok);
    except _Out:
        return None


def in_band(value, lo, hi):
    try:
        return ((lo) <= (value)) and ((value) <= (hi));
    except _Out:
        return None


def is_score_valid(points):
    try:
        band = _call(grade, points);
        return ((band) >= (3)) and ((band) <= (5));
    except _Out:
        return None


def grade(points):
    try:
        if (points) >= (90):
            return 5;
        elif (points) >= (75):
            return 4;
        elif (points) >= (60):
            return 3;
        else:
            return 0;
    except _Out:
        return None
