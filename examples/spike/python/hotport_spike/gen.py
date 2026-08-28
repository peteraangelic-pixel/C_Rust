"""Zestawy testowe dla silnika różnicowego.

L1 (replay): przypadki zhak... spisane 1:1 z tests/test_{slug,uuid,ip_address}.py
vendora + złote reguły z probe'ów empirycznych (REPORT.md).
L2 (property-based, seedowane): generatory deterministyczne + mutacje adversarialne.

Model przypadku: {"fn": "slug"|"uuid"|"ipv4", "value": ..., "kwargs": {...},
                  "origin": "l1"|"l2"} — oczekiwanego wyniku NIE zapisujemy:
prawdą jest to, co zwraca oryginał Pythona (differential, nie golden files).
"""

import random

# ---------------------------------------------------------------- L1: replay

L1 = []


def _l1(fn, value, **kwargs):
    L1.append({"fn": fn, "value": value, "kwargs": kwargs, "origin": "l1"})


# tests/test_slug.py (+ pułapka końcowego '\n' — semantyka '$' w re)
for v in ["123-asd-7sda", "123-k-123", "dac-12sa-459", "dac-12sa7-ad31as", "my-slug-2134", "abc\n"]:
    _l1("slug", v)
for v in ["some.slug&", "1231321%", "   21312", "-47q-p--123", "my.slug", "abc\n\n", "abc\r"]:
    _l1("slug", v)

# tests/test_uuid.py (+ obiekty UUID → routing)
from uuid import uuid4 as _uuid4  # noqa: E402

for v in [
    "2bc1c94f-0deb-43e9-92a1-4775189ec9f8",
    "888256d7c49341f19fa33f29d3f820d7",
]:
    _l1("uuid", v)
_l1("uuid", _uuid4())  # UUID object → core zwróci None (routing)
for v in [
    "2bc1c94f-deb-43e9-92a1-4775189ec9f8",
    "2bc1c94f-0deb-43e9-92a1-4775189ec9f",
    "gbc1c94f-0deb-43e9-92a1-4775189ec9f8",
    "2bc1c94f 0deb-43e9-92a1-4775189ec9f8",
]:
    _l1("uuid", v)

# złote reguły uuid z probe'ów (bug-for-bug!)
for v in [
    "2BC1C94F-0DEB-43E9-92A1-4775189EC9F8",   # upper hex ok
    "{2bc1c94f-0deb-43e9-92a1-4775189ec9f8}", # braces ok
    "urn:uuid:2bc1c94f-0deb-43e9-92a1-4775189ec9f8",
    "{urn:uuid:2bc1c94f-0deb-43e9-92a1-4775189ec9f8}",
    "uuid:2bc1c94f-0deb-43e9-92a1-4775189ec9f8",  # 'uuid:' bez 'urn:' — ok!
    "URN:UUID:2bc1c94f-0deb-43e9-92a1-4775189ec9f8",  # WIELKIE urn → invalid
    "+2bc1c94f0deb43e992a14775189ec9f",   # '+' + 31 hex = VALID (int!)
    "-2bc1c94f0deb43e992a14775189ec9f",   # '-' + 31 hex bez myślników → po replace 31 → invalid
    "-2bc1c94f-0deb-43e9-92a1-4775189ec9f8",  # '-' + kanoniczny → po replace 32 hex → VALID (!)
    "2bc1c94f_0deb43e992a14775189ec9f",   # PEP 515 '_' → VALID
    "2bc1c94f0deb43e992a14775189ec9_f",   # trailing _f → VALID
    "2bc1c94f0deb43e992a14775189ec9f_",   # trailing '_' → invalid (len 33)
    "2bc1c94f0deb43e992a14775189ec9  ",   # 30hex + 2 spacje → VALID (!)
    "\t2bc1c94f0deb43e992a14775189ec9 ",  # mieszane ws → VALID
    "\x0b2bc1c94f0deb43e992a14775189ec9f",  # \x0b → VALID (int obcina)
    "+\x0b2bc1c94f0deb43e992a14775189ec",   # ws w środku → invalid
    " 2bc1c94f0deb43e992a14775189ec9f8 ",   # 33 znaki → invalid
    "٢bc1c94f0deb43e992a14775189ec9f8",   # unicode Nd → POZA KONTRAKTEM (routing)
]:
    _l1("uuid", v)
_l1("uuid", 123)  # AttributeError wycieka w oryginale — parzystość API!

# tests/test_ip_address.py (reprezentatywny przekrój + kombinacje kwargs)
for v in ["127.0.0.1", "123.5.77.88", "12.12.12.12", "0.0.0.0"]:
    _l1("ipv4", v)
for v, kw in [
    ("127.0.0.1/0", dict(cidr=True, strict=True, host_bit=True)),
    ("123.5.77.88", dict(cidr=True, strict=False, host_bit=True)),
    ("12.12.12.0/24", dict(cidr=True, strict=True, host_bit=False)),
    ("12.12.12.0/24", dict(cidr=True, strict=True, host_bit=True)),
    ("1.2.3.4/24", dict(cidr=True, strict=False, host_bit=True)),
    ("1.1.1.1/1", dict(cidr=False, strict=True, host_bit=True)),
    ("1.1.1.1/33", dict(cidr=True, strict=False, host_bit=True)),
    ("1.1.1.1/24", dict(cidr=True, strict=True, host_bit=False)),
    ("1.1.1.1", dict(cidr=True, strict=True, host_bit=True)),      # strict wymaga '/'
    ("1.2.3.4/24", dict(cidr=True, strict=False, host_bit=False)),  # bity hosta
]:
    _l1("ipv4", v, **kw)
# złote reguły ipv4 z probe'ów
for v in [
    "900.200.100.75", "0127.0.0.1", "abc.0.0.1", " 1.1.1.1", "1.1.1.1 ",
    "1.1.1.1/024", "1.1.1.1/000024", "1.1.1.1/00", "1.1.1.1/255.255.255.0",
    "1.1.1.1/0.0.0.0", "1.1.1.1/255.255.0.0", "1.1.1.1/255.0.255.0",
    "1.1.1.1/8.8.8.8", "1.1.1.1/255.255.255.00", "1.1.1.1/+24", "1.1.1.1/-1",
    "1.1.1.1/2_4", "1.1.1.1/24 ", "1.1.1.1/ 24", "1.1.1.1/24/24", "1.1.1.1/",
    "01.1.1.1/8", "1.1.1.01", "1.1.1", "1.1.1.1.", "1.1.1.256",
]:
    _l1("ipv4", v)
_l1("ipv4", "")  # oryginał: False (falsy guard)
_l1("slug", "")
_l1("uuid", "")


# ---------------------------------------------------------------- L2: seeded

_HEX = "0123456789abcdef"
_AL = "abcdefghijklmnopqrstuvwxyz0123456789"


def _rand_slug(rng):
    n = rng.randint(1, 6)
    parts = ["".join(rng.choice(_AL) for _ in range(rng.randint(1, 8))) for _ in range(n)]
    return "-".join(parts)


def _rand_uuid(rng):
    return "".join(rng.choice(_HEX) for _ in range(8)) + "-" + \
           "-".join("".join(rng.choice(_HEX) for _ in range(k)) for k in (4, 4, 4, 12))


def _rand_ipv4(rng):
    octets = [str(rng.randint(0, 255)) for _ in range(4)]
    s = ".".join(octets)
    r = rng.random()
    if r < 0.4:
        return s
    if r < 0.8:
        return f"{s}/{rng.randint(0, 32)}"
    masks = ["255.255.255.0", "255.255.0.0", "255.0.0.0", "0.0.0.0", "255.255.255.255"]
    return f"{s}/{rng.choice(masks)}"


def _mutate(rng, s):
    """Adversarialne mutacje: wcięcia, wielkość liter, znaki specjalne, obcięcia."""
    ops = [
        lambda x: " " + x, lambda x: x + " ", lambda x: x.upper(), lambda x: x.lower(),
        lambda x: x[:-1] if x else x, lambda x: "{" + x + "}",
        lambda x: "urn:uuid:" + x, lambda x: x.replace("-", "", 1),
        lambda x: x + "-", lambda x: "-" + x, lambda x: x.replace(".", ".0", 1),
        lambda x: x + "/24", lambda x: "_" + x, lambda x: x + "_",
        lambda x: x.replace("a", "A", 1) if "a" in x else x,
        lambda x: "\t" + x + "\n", lambda x: x + "0", lambda x: "0" + x,
        lambda x: x + "١",  # arabska 1 → non-ASCII → routing
        lambda x: x.replace("1", "١", 1) if "1" in x else x,
    ]
    for _ in range(rng.randint(1, 2)):
        s = rng.choice(ops)(s)
        if not s:
            break
    return s


def generate(seed=42, per_fn=250):
    """Deterministyczny zestaw L2: poprawne + zmutowane + czyste edge-case'y."""
    rng = random.Random(seed)
    out = []
    gens = {"slug": _rand_slug, "uuid": _rand_uuid, "ipv4": _rand_ipv4}
    for fn, gen in gens.items():
        for _ in range(per_fn):
            base = gen(rng)
            out.append({"fn": fn, "value": base, "kwargs": {}, "origin": "l2"})
            out.append({"fn": fn, "value": _mutate(rng, base), "kwargs": {}, "origin": "l2"})
        # dodatkowe kombinacje kwargs dla ipv4
        if fn == "ipv4":
            for i in range(per_fn // 2):
                base = gen(rng)
                kw = dict(
                    cidr=bool(rng.randint(0, 1)),
                    strict=bool(rng.randint(0, 1)),
                    host_bit=bool(rng.randint(0, 1)),
                )
                out.append({"fn": "ipv4", "value": base, "kwargs": kw, "origin": "l2"})
    # stałe edge-case'y (K6): puste, graniczne, unicode
    for fn in ("slug", "uuid", "ipv4"):
        for v in ["", " ", "\n", "0", "-", "_", "a", "Æ", "日本", "\x00", "a" * 100, "9" * 45]:
            out.append({"fn": fn, "value": v, "kwargs": {}, "origin": "l2-edge"})
    return out


def all_cases(seed=42, per_fn=250):
    return L1 + generate(seed=seed, per_fn=per_fn)


# ---------------------------------------------------------------- demo (translator v0)

DEMO_L1 = [
    {"fn": "in_band", "args": [0.5, 0.0, 1.0], "kwargs": {}, "origin": "l1"},
    {"fn": "in_band", "args": [500.0, float("-inf"), 400.0], "kwargs": {}, "origin": "l1"},
    {"fn": "grade", "args": [95.0], "kwargs": {}, "origin": "l1"},
    {"fn": "grade", "args": [59.99], "kwargs": {}, "origin": "l1"},
    {"fn": "sum_upto", "args": [10], "kwargs": {}, "origin": "l1"},
    {"fn": "sum_upto", "args": [0], "kwargs": {}, "origin": "l1"},
    {"fn": "code_ok", "args": ["AB-1234-CD", "AB"], "kwargs": {}, "origin": "l1"},
    {"fn": "code_ok", "args": ["short", "s"], "kwargs": {}, "origin": "l1"},
]


def demo_cases(seed=99, per_fn=120):
    """Zestaw L2 dla celów translatora v0 — z granicami K3 (i64!) i K2 (NaN/inf)."""
    rng = random.Random(seed)
    out = list(DEMO_L1)

    def add(fn, *a):
        out.append({"fn": fn, "args": list(a), "kwargs": {}, "origin": "l2-demo"})

    fast_ns = [0, 1, 5, 100, 1000, 20_000, -5]
    for _ in range(per_fn):
        add("in_band", rng.uniform(-100, 100), rng.uniform(-100, 100), rng.uniform(-100, 100))
        add("grade", rng.uniform(-10, 110))
        add("sum_upto", rng.choice(fast_ns + [rng.randint(-100, 2000)]))
        # granice K3 na O(1): safe_mul (oracle natychmiast, rdzeń checked_mul)
        a = rng.choice([rng.randint(-10, 10), rng.randint(-(2**62), 2**62), 2**62, -(2**63), 2**63 - 1, 2**63])
        b = rng.choice([rng.randint(-10, 10), rng.randint(-4, 4), 2**31, 2**63 - 1, 2])
        add("safe_mul", a, b)
        code = "".join(rng.choice("ab12-") for _ in range(rng.randint(0, 14)))
        add("code_ok", code, rng.choice(["a", "b", "ab", "x", ""]))
    # v0.1: krawędzie // i % (floor/znak dzielnika; b==0; granice i64)
    div_edges = [(-7, 2), (7, -2), (-7, -2), (7, 2), (-1, 5), (1, -5), (0, 3), (3, 1),
                 (1, 0), (0, 0), (-9, 3), (2**62, 2), (-(2**62), 2), (-(2**63), -1), (2**63 - 1, 2)]
    for a, b in div_edges:
        add("floor_div", a, b)
        add("py_mod", a, b)
    for a in [0, 1, -1, 5, -(2**63), 2**62, 2**63 - 1, 2**63]:
        add("negate", a)
    # stratyfikowane krawędzie mnożenia (przepełnienia i okoliczne wartości)
    for a, b in [(2, 3), (0, 2**63 - 1), (2**62, 1), (2**62, 2), (2**31, 2**31),
                 (2**63 - 1, 2), (-(2**63), 1), (-(2**63), 2), (-1, 2**63 - 1),
                 (3_037_000_499, 3_037_000_500), (2**40, 2**23), (2**63, 1), (2**63 + 1, 1)]:
        add("safe_mul", a, b)
    # unicode: len w punktach kodowych (chars().count() w rust — pułapka bajtów)
    add("code_ok", "ńą日本語123-", "ń")
    for f in [0.0, -0.0, 1.0, -1.0, 90.0, 89.999999, 75.0, 60.0, 59.9,
              float("inf"), float("-inf"), float("nan"), 1e308, -1e308, 0.1, -0.1]:
        add("in_band", f, -1000.0, 1000.0)
        add("grade", f)
    return out


def cluster_cases(seed=123, per_fn=150):
    """Przypadki dla KLASTRA admission (v0.2): entry + argumenty 3x float."""
    rng = random.Random(seed)
    out = [
        {"fn": "admission", "args": [80.0, 0.0, 100.0], "kwargs": {}, "origin": "l1"},
        {"fn": "admission", "args": [50.0, 0.0, 100.0], "kwargs": {}, "origin": "l1"},
        {"fn": "admission", "args": [75.0, 0.0, 100.0], "kwargs": {}, "origin": "l1"},
    ]

    def add(p, lo, hi):
        out.append({"fn": "admission", "args": [p, lo, hi], "kwargs": {},
                    "origin": "l2-cluster"})

    for _ in range(per_fn):
        add(rng.uniform(-10, 110), rng.uniform(-10, 110), rng.uniform(-10, 110))
    for f in [0.0, 59.99, 60.0, 74.99, 75.0, 89.99, 90.0, 100.0,
              float("nan"), float("inf"), float("-inf")]:
        add(f, 0.0, 100.0)
    return out
