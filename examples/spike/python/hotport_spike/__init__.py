"""hotport_spike — shim fazy 0 (PLAN.md, Zasada Z1/Z4).

Drop-in zamiennik validators.slug / validators.uuid / validators.ipv4:
API 1:1 dzięki REUŻYCIU ich własnego dekoratora @validator (identyczna
konwersja wyniku → True/ValidationError, identyczna obsługa wyjątków).

Tryby (HOTPORT_IMPL): python | rust | both (kanarek — porównuje i alarmuje).
Backend (HOTPORT_BACKEND): rust (ctypes .so; domyślny gdy dostępny) | ref
(wykonawcza specyfikacja rdzenia — używana w testach i gdy brak .so).

Routing per WEJŚCIE (nie per funkcja): rdzeń zwraca None → wywołanie trafia
do oryginału Pythona. To kluczowa decyzja architektoniczna spike'a (Z5):
kontrakt ASCII zamiast replikacji pełnej luźności Pythona (unicode Nd w int()!).
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_VALIDATORS_SRC = os.path.normpath(
    os.path.join(_HERE, "..", "..", "..", "targets", "validators", "src")
)
if _VALIDATORS_SRC not in sys.path:
    sys.path.insert(0, _VALIDATORS_SRC)

import validators  # vendored 0.35.0 (examples/targets/validators)
from validators.utils import validator  # reużycie = parzystość API z definicji

from . import ref_backend, rust_backend

__all__ = ["slug", "uuid", "ipv4", "CanaryMismatch", "set_mode", "active_backend"]


class CanaryMismatch(RuntimeError):
    """Tryb 'both': rdzeń i oryginał dały różne wyniki — łapiemy NA ŻYWO."""


def _initial_mode():
    m = os.environ.get("HOTPORT_IMPL", "python").lower()
    return m if m in ("python", "rust", "both") else "python"


_MODE = _initial_mode()


def set_mode(mode):
    """Przełącz tryb w locie (testy/canary); zwraca poprzedni."""
    global _MODE
    if mode not in ("python", "rust", "both"):
        raise ValueError("tryb: python | rust | both")
    prev, _MODE = _MODE, mode
    return prev


def active_backend():
    """Backend rdzenia: obiekt z CORES {slug,uuid,ipv4}."""
    pref = os.environ.get("HOTPORT_BACKEND", "").lower()
    if pref == "ref" or (pref != "rust" and not rust_backend.available()):
        return ref_backend
    return rust_backend


_PY = {"slug": validators.slug, "uuid": validators.uuid, "ipv4": validators.ipv4}


def _py_bool(name, value, kwargs):
    """Oryginalny predykat jako bool; wyjątki PRZECHODZĄ (parzystość API)."""
    return bool(_PY[name](value, **kwargs))


def _dispatch(name, value, kwargs):
    """Serce shimu: predykat bool albo wyjątek identyczny z oryginałem."""
    backend = active_backend()
    core = None
    if _MODE in ("rust", "both"):
        core = backend.CORES[name]
    if core is not None:
        res = core(value, **kwargs)
        if res is not None:
            if _MODE == "both":
                py = _py_bool(name, value, kwargs)
                if py != res:
                    raise CanaryMismatch(
                        f"{name}({value!r}, {kwargs}): python={py}, backend={backend.NAME}:{res}"
                    )
                return py
            return res
        # None → wejście poza kontraktem → spadamy do oryginału (routing per input)
    return _py_bool(name, value, kwargs)


@validator
def slug(value, /):
    """Drop-in validators.slug — patrz moduł docstring."""
    return _dispatch("slug", value, {})


@validator
def uuid(value, /):
    """Drop-in validators.uuid — UUID object i int(y) obsługiwane przez routing."""
    return _dispatch("uuid", value, {})


@validator
def ipv4(value, /, *, cidr=True, strict=False, private=None, host_bit=True):
    """Drop-in validators.ipv4 — private≠None routowane do oryginału (poza MVP)."""
    if private is not None:
        return _py_bool("ipv4", value, dict(cidr=cidr, strict=strict, private=private, host_bit=host_bit))
    return _dispatch("ipv4", value, dict(cidr=cidr, strict=strict, host_bit=host_bit))
