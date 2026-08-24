"""Backend Rust przez ctypes — ładowany z libhotport_spike_core.so.

Ścieżka "sandboxowa" (bez crates.io/PyO3): FFI C-ABI z examples/spike/core/src/ffi.rs.
Umowa FFI: 1 = true, 0 = false, -1 = poza kontraktem (→ routing do Pythona).

W CI ta sama logika wołana jest też przez PyO3 (examples/spike/pyo3) —
weryfikacja differential pokrywa oba transporty, bo wołają identyczne rdzenie.
"""

import ctypes
import os

_lib = None
_load_error = None

_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "target", "release", "libhotport_spike_core.so",
)


def _load():
    global _lib, _load_error
    if _lib is not None or _load_error is not None:
        return
    path = os.environ.get("HOTPORT_SO", _DEFAULT)
    if not os.path.exists(path):
        _load_error = f"brak biblioteki: {path} (zbuduj: cargo build --release -p hotport-spike-core)"
        return
    lib = ctypes.CDLL(path)
    for fn, restype in [
        ("hotport_slug_is_valid", ctypes.c_int),
        ("hotport_uuid_is_valid", ctypes.c_int),
        ("hotport_ipv4_is_valid", ctypes.c_int),
    ]:
        getattr(lib, fn).restype = restype
    lib.hotport_slug_is_valid.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    lib.hotport_uuid_is_valid.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    lib.hotport_ipv4_is_valid.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_byte, ctypes.c_byte, ctypes.c_byte]
    _lib = lib


def _encode(value):
    """str → bytes; nie-str → None (routing do Pythona — Z5/ADR-0005).

    UWAGA (bug #6, złapany przez CI na prawdziwym .so): wcześniejsza wersja
    robiła `bool(_call_str(...))`, czyli `bool(None)` → False dla nie-stringów
    (np. obiektów UUID!) zamiast None=routing. Ref-backend miał dobrze —
    dlatego różnica wyszła dopiero na skompilowanym Rust w CI.
    """
    if not isinstance(value, str):
        return None
    return value.encode("utf-8")


def slug_core(value):
    _load()
    if _lib is None:
        raise RuntimeError(_load_error)
    data = _encode(value)
    if data is None:
        return None  # poza kontraktem → oryginał Pythona
    r = _lib.hotport_slug_is_valid(data, len(data))
    return None if r == -1 else bool(r)


def uuid_core(value):
    _load()
    if _lib is None:
        raise RuntimeError(_load_error)
    data = _encode(value)
    if data is None:
        return None  # np. obiekt UUID/int → oryginał (uuid(UUID)=True, uuid(123)=AttributeError!)
    r = _lib.hotport_uuid_is_valid(data, len(data))
    return None if r == -1 else bool(r)


def ipv4_core(value, cidr=True, strict=False, host_bit=True):
    _load()
    if _lib is None:
        raise RuntimeError(_load_error)
    data = _encode(value)
    if data is None:
        return None
    r = _lib.hotport_ipv4_is_valid(data, len(data), bool(cidr), bool(strict), bool(host_bit))
    return None if r == -1 else bool(r)


def available():
    _load()
    return _lib is not None


def why_unavailable():
    _load()
    return _load_error


NAME = "rust"

CORES = {"slug": slug_core, "uuid": uuid_core, "ipv4": ipv4_core}
