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



def in_band(value, lo, hi):
    try:
        return ((lo) <= (value)) and ((value) <= (hi));
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


def sum_upto(n):
    try:
        if not (-9223372036854775808 <= n <= 9223372036854775807): raise _Out()
        total = 0;
        for i in range(1, _bin('a', n, 1)):
            total = _bin('a', total, i);
        return total;
    except _Out:
        return None


def safe_mul(a, b):
    try:
        if not (-9223372036854775808 <= a <= 9223372036854775807): raise _Out()
        if not (-9223372036854775808 <= b <= 9223372036854775807): raise _Out()
        return _bin('m', a, b);
    except _Out:
        return None


def code_ok(code, prefix):
    try:
        if (len(code)) != (10):
            return False;
        return (code.startswith(prefix)) and ((not code.endswith('-')));
    except _Out:
        return None
