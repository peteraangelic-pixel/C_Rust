# Spike fazy 0 — ręczny port 3 funkcji `validators` + silnik differential

Cel (PLAN.md §Faza 0): **udowodnić, nie założyć**, że semantykę da się przenieść
i zweryfikować — zanim powstanie jakikolwiek automatyczny translator.

## Co tu jest

| Ścieżka | Co robi |
|---|---|
| `core/` | Rdzeń Rust (std-only): `slug_core`, `uuid_core`, `ipv4_core` + FFI C-ABI + testy jednostkowe ze złotych reguł |
| `pyo3/` | Binding PyO3 (osobny workspace; budowany w CI — ADR-0004) |
| `python/hotport_spike/` | Shim API 1:1 (reużywa dekorator `@validator`), backendy `ref`/`rust`, generatory L1/L2, silnik differential z bramką, benchmark |
| `python/hotport_tracer/` | **Tracer v1 (Faza 1)**: ślad wywołań → manifest `hotport.manifest/0.1.0` (kształty typów, K4, ASCII, replay) |
| `python/hotport_trans/` | **Translator v0 (Faza 2)**: podzbiór Pythona → Rust (golden `.rs`) + cień (wykonywalna specyfikacja reguł) |
| `generated/` | Artefakty translatora (commitowane golden): `*.rs`, `shadow_generated.py` |
| `tests/` | pytest: differential, czułość bramki (wstrzyknięte bugi), parzystość API, kanarek `both`, tracer + integracja end-to-end |
| `report/` | Generowane raporty (differential-*.md, bench.md) |
| `manifest-validators.json` | Artefakt: manifest ze śladu suite vendora (commitowany jako dowód) |

## Uruchomienie (sandbox, bez toolchaina Rusta)

```bash
pip install pytest

# differential + bramka + benchmark (działa bez toolchaina Rusta)
python -m pytest examples/spike -q
python examples/spike/python/hotport_spike/runner.py --backend ref

# Faza 1: ślad prawdziwej suite → manifest → differential (pętla zamknięta)
PYTHONPATH=examples/spike/python:examples/targets/validators/src \
  python -m hotport_tracer --module validators --names slug uuid ipv4 \
  --pytest examples/targets/validators/tests/test_slug.py \
             examples/targets/validators/tests/test_uuid.py \
             examples/targets/validators/tests/test_ip_address.py \
  --out examples/spike/manifest-validators.json
python examples/spike/python/hotport_spike/runner.py --backend ref \
  --manifest examples/spike/manifest-validators.json
```

## Uruchomienie (z toolchainem Rusta — pełna ścieżka)

```bash
cargo build --release -p hotport-spike-core     # produkuje libhotport_spike_core.so
python -m pytest examples/spike -q              # differential liczy też backend rust
python examples/spike/python/hotport_spike/runner.py --backend rust  # bramka na RUST
python examples/spike/python/hotport_spike/bench.py                 # kolumna py/rust
```

## Zmienne środowiskowe

* `HOTPORT_IMPL` = `python` | `rust` | `both` (domyślnie `python`) — tryb shimu;
  `both` = kanarek: porównuje wyniki na żywo i rzuca `CanaryMismatch` (Z4).
* `HOTPORT_BACKEND` = `rust` | `ref` — backend rdzenia (domyślnie rust, jeśli
  jest `.so`, inaczej ref).
* `HOTPORT_SO` — ścieżka do `libhotport_spike_core.so` (nadpisywanie domyślnej).

## Uczciwa interpretacja benchmarku

* Kolumna `ref` to **pythonowa** specyfikacja rdzenia (bez `re`/`ipaddress`/`uuid`)
  — pokazuje koszt samej logiki, NIE speedup z Rusta.
* Kolumna `rust` (ctypes) zawiera podatek FFI ~0,3–1 µs/wywołanie — to ryzyko R2
  z PLAN.md. Wniosek architektoniczny: tłumaczyć **klastry** funkcji (jedno
  przejście przez granicę), nie liście; docelowo PyO3 zamiast ctypes.
