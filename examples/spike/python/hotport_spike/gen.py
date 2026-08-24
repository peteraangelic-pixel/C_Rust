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
