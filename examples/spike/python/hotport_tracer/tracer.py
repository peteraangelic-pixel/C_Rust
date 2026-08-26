"""Rejestrator wywołań: wrap funkcji modułu + zapis kształtów/próbek/czasów.

Zasada: niczego nie zgadujemy — wszystko zaobserwowane (probe-first).
v0.1 śledzi: liczniki, czas własny, kształty typów (arg/wynik), wyjątki,
mutacje kontenerów (K4, snapshoty przed/po), frakcję ASCII (ADR-0005)
oraz próbki replay (dedup + capy) do warstwy L1 differentialu.
"""

import functools
import inspect
import time
import uuid as uuid_mod

MAX_REPR = 2000  # cap próbki (ochrona rozmiaru)


def shape_of(v):
    """Kształt wartości jako czytelny string (manifest v0.1)."""
    t = type(v)
    if v is None:
        return "None"
    if t is bool:
        return "bool"
    if t is int:
        return "int"
    if t is float:
        return "float"
    if t is str:
        return "str"
    if t is bytes:
        return "bytes"
    if t is list:
        inner = sorted({shape_of(x) for x in v[:10]}) or ["empty"]
        return f"list[{'|'.join(inner)}]"
    if t is tuple:
        return "tuple(" + ",".join(shape_of(x) for x in v[:10]) + ")"
    if t is dict:
        k = sorted({shape_of(x) for x in list(v)[:10]}) or ["empty"]
        w = sorted({shape_of(x) for x in list(v.values())[:10]}) or ["empty"]
        return f"dict[{'|'.join(k)}->{'|'.join(w)}]"
    if t is set:
        inner = sorted({shape_of(x) for x in list(v)[:10]}) or ["empty"]
        return f"set[{'|'.join(inner)}]"
    return f"{t.__module__}.{t.__qualname__}"


def _snapshot(v):
    """Snapshot do detekcji mutacji (K4): tylko kontenery mutowalne."""
    if isinstance(v, (list, dict, set, bytearray)):
        try:
            return repr(v)[:MAX_REPR]
        except Exception:  # noqa: BLE001 — repr może być zepsuty
            return None
    return None


def encode_value(v):
    """Wartość → JSON-safe; odtwarzalna dla str/int/float/bool/None/UUID."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, uuid_mod.UUID):
        return {"$uuid": v.hex}
    return {"$repr": repr(v)[:200]}  # nieodtwarzalna → tylko podgląd


def decode_value(v):
    """Odwrotność encode_value (dla replay). None = nieodtwarzalna."""
    if isinstance(v, dict):
        if "$uuid" in v:
            return uuid_mod.UUID(hex=v["$uuid"])
        return None
    return v


class _FnStats:
    __slots__ = ("calls", "self_ns", "durations", "arg_shapes", "ret_shapes",
                 "raises", "mutated", "samples", "seen_samples",
                 "truthy", "ascii_strs", "total_strs", "callers")

    def __init__(self):
        self.calls = 0
        self.self_ns = 0
        self.durations = []
        self.arg_shapes = {}   # slot (nazwa parametru / p<N> / kwarg) -> set[str]
        self.ret_shapes = set()
        self.raises = []
        self.mutated = False
        self.samples = []
        self.seen_samples = set()
        self.truthy = 0        # wyniki prawdziwościowo (dla predykatów)
        self.ascii_strs = 0
        self.total_strs = 0
        self.callers = {}      # caller -> licznik (call-graph, manifest 0.2.0)


def _record_arg(st, slot, v):
    st.arg_shapes.setdefault(slot, set()).add(shape_of(v))
    if isinstance(v, str):
        st.total_strs += 1
        if v.isascii():
            st.ascii_strs += 1


class Tracer:
    """Wrapuje funkcje modułu i zbiera dane do manifestu.

    Użycie:
        t = Tracer()
        t.wrap_module(validators, names=["slug", "uuid", "ipv4"])
        pytest.main([testpaths, "-q"])          # albo dowolny kod klienta
        manifest = t.manifest(target_module="validators")
    """

    def __init__(self, max_samples=25, max_samples_total=500):
        self.max_samples = max_samples
        self.max_samples_total = max_samples_total
        self._stats = {}       # (module, qualname) -> _FnStats
        self._wrapped = []     # [(module, name, original), ...]
        self._stack = []       # stos wywołań do call-graph (jednowątkowo w v0.2)

    def wrap_module(self, module, names=None):
        if names is None:
            names = [n for n in dir(module)
                     if callable(getattr(module, n)) and not n.startswith("_")
                     and getattr(getattr(module, n), "__module__", None) == module.__name__]
            if not names:
                # fallback (np. moduły syntetyczne/tests, gdzie __module__ wskazuje
                # inaczej) — wszystkie publiczne callable
                names = [n for n in dir(module)
                         if callable(getattr(module, n)) and not n.startswith("_")]
        for name in names:
            original = getattr(module, name)
            # klucz = nazwa atrybutu w module (dla funkcji modułowych == qualname;
            # dla zagnieżdżonych/dekorowanych qualname może zawierać <locals>)
            key = (module.__name__, name)
            try:
                params = list(inspect.signature(original).parameters)
            except (ValueError, TypeError):
                params = []
            self._stats.setdefault(key, _FnStats())
            self._wrapped.append((module, name, original))

            @functools.wraps(original)
            def wrapper(*args, __key=key, __orig=original, __params=params, **kwargs):
                st = self._stats[__key]
                st.calls += 1
                # krawędź call-graph [REVIEW pkt 9]: kto mnie woła?
                caller = self._stack[-1][1] if self._stack else "<root>"
                st.callers[caller] = st.callers.get(caller, 0) + 1
                self._stack.append(__key)
                # kształty + snapshoty do detekcji mutacji
                watched = []  # [(referencja, przed)]
                for i, a in enumerate(args):
                    _record_arg(st, __params[i] if i < len(__params) else f"p{i}", a)
                    before = _snapshot(a)
                    if before is not None:
                        watched.append((a, before))
                for k, v in kwargs.items():
                    _record_arg(st, k, v)
                    before = _snapshot(v)
                    if before is not None:
                        watched.append((v, before))
                # próbka replay (dedup + capy)
                try:
                    sig = repr(args)[:MAX_REPR] + "|" + repr(sorted(kwargs.items()))[:MAX_REPR]
                except Exception:  # noqa: BLE001
                    sig = None
                if (
                    sig is not None
                    and sig not in st.seen_samples
                    and len(st.samples) < self.max_samples
                    and sum(len(s.samples) for s in self._stats.values()) < self.max_samples_total
                ):
                    st.seen_samples.add(sig)
                    st.samples.append({
                        "args": [encode_value(a) for a in args],
                        "kwargs": {k: encode_value(v) for k, v in kwargs.items()},
                    })
                # wywołanie + czas własny
                t0 = time.perf_counter_ns()
                try:
                    result = __orig(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 — klasyfikujemy wszystkie
                    if type(e).__name__ not in st.raises:
                        st.raises.append(type(e).__name__)
                    raise
                finally:
                    self._stack.pop()
                    dt = time.perf_counter_ns() - t0
                    st.self_ns += dt
                    if len(st.durations) < 10_000:
                        st.durations.append(dt)
                # K4: czy wywołanie zmutowało argumenty?
                for ref, before in watched:
                    if _snapshot(ref) != before:
                        st.mutated = True
                st.ret_shapes.add(shape_of(result))
                try:
                    if bool(result):
                        st.truthy += 1
                except Exception:  # noqa: BLE001
                    pass
                return result

            setattr(module, name, wrapper)
        return self

    def unwrap_all(self):
        for module, name, original in self._wrapped:
            setattr(module, name, original)
        self._wrapped = []

    def stats_for(self, module_name, qualname):
        return self._stats.get((module_name, qualname))

    def manifest(self, target_module="?", command=None):
        from .manifest import build_manifest
        return build_manifest(self._stats, target_module=target_module, command=command)
