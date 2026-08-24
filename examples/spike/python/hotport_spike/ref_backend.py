"""Backend referencyjny — WYKONYWALNA SPECYFIKACJA przyszłego rdzenia Rust.

Celowo nie używa re/ipaddress/uuid: każda linijka jest 1:1 z algorytmem
w examples/spike/core/src/lib.rs. Jeśli differential (tests/test_differential.py)
wykryje rozbieżność z validators → albo specyfikacja jest zła, albo port —
w obu przypadkach MUSI to wyjść przed promocją (Z2/Z5).

None = wejście poza kontraktem → routing do oryginału Pythona.
"""

WS_INT = " \t\n\r\x0b\x0c"  # zbiór białych znaków obcinanych przez int() (empirycznie)


def slug_core(value):
    """`^[a-z0-9]+(?:-[a-z0-9]+)*$` + pusty string → False.

    PUŁAPKA: '$' w Pythonie dopasowuje też przed JEDNYM końcowym '\\n'
    (validators.slug('abc\\n') → True). Obcinamy więc max jeden '\\n'.
    """
    body = value[:-1] if value.endswith("\n") else value
    if not body:
        return False
    seen_hyphen = True  # start = jak po hyphenie: wiodowy '-' zabroniony (^[a-z0-9]+)
    for ch in body:
        alnum = ("a" <= ch <= "z") or ("0" <= ch <= "9")
        if alnum:
            seen_hyphen = False
        elif ch == "-" and not seen_hyphen:
            seen_hyphen = True
        else:
            return False
    return not seen_hyphen


def uuid_core(value):
    """uuid.UUID(str) w wersji bug-for-bug ASCII (złote reguły z probe'ów)."""
    if not isinstance(value, str) or not value.isascii():
        return None  # poza kontraktem ASCII (unicode Nd / unicode ws w int())
    t = value.replace("urn:", "").replace("uuid:", "")  # małe litery, wszędzie
    t = t.strip("{}")  # zbiór znaków {,} na końcach (nie prefiks!)
    t = t.replace("-", "")
    if len(t) != 32:  # '+' i '_' i ws LICZĄ się do długości
        return False
    g = t.strip(WS_INT)  # int() obcina białe znaki na końcach
    i = 1 if g.startswith("+") else 0
    if i >= len(g):
        return False  # sam '+' → int('+') to błąd
    any_digit = False
    last = "start"  # start | digit | underscore
    for c in g[i:]:
        if c in "0123456789abcdefABCDEF":
            any_digit = True
            last = "digit"
        elif c == "_":
            if last != "digit":
                return False  # PEP 515: pojedynczo, między cyframi
            last = "underscore"
        else:
            return False
    return any_digit and last == "digit"


def _parse_octet(s):
    """ipaddress._parse_octet: ASCII-cyfry, bez wiodących zer, 0–255."""
    if not s or not s.isascii() or not s.isdigit():
        return None
    if len(s) > 1 and s[0] == "0":
        return None
    v = int(s)
    return v if v <= 255 else None


def _parse_dotted(s):
    parts = s.split(".")
    if len(parts) != 4:
        return None
    v = 0
    for p in parts:
        o = _parse_octet(p)
        if o is None:
            return None
        v = (v << 8) | o
    return v


def _parse_netmask(s):
    """Prefix (wiodące zera DOZWOLONE — asymetria!) albo ciągła maska kropkowana."""
    if "." in s:
        m = _parse_dotted(s)
        if m is None:
            return None
        for p in range(33):
            mask = 0 if p == 0 else ((0xFFFFFFFF << (32 - p)) & 0xFFFFFFFF)
            if m == mask:
                return p
        return None  # nieciągła (255.0.255.0) lub nie-maska (8.8.8.8)
    if not s or not s.isascii() or not s.isdigit():
        return None  # '+24', ' 24', '٣٢', '2_4', ''
    p = int(s)
    return p if p <= 32 else None


def ipv4_core(value, cidr=True, strict=False, host_bit=True):
    """validators.ipv4 (private=None) wg semantyki ipaddress (3.9.5+)."""
    if not isinstance(value, str) or not value.isascii():
        return None
    if not value:
        return False
    if not cidr:
        return _parse_dotted(value) is not None
    if strict and value.count("/") != 1:
        return False
    if "/" in value:
        addr_s, mask_s = value.split("/", 1)
        plen = _parse_netmask(mask_s)
        if plen is None:
            return False
    else:
        addr_s, plen = value, 32
    addr = _parse_dotted(addr_s)
    if addr is None:
        return False
    host_mask = 0xFFFFFFFF if plen == 0 else ((1 << (32 - plen)) - 1)
    if not host_bit and (addr & host_mask) != 0:
        return False  # IPv4Network(strict=True): bity hosta zerem
    return True


NAME = "ref"

CORES = {"slug": slug_core, "uuid": uuid_core, "ipv4": ipv4_core}
