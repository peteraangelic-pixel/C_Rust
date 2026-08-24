# hotport — przyspieszanie bibliotek Python przez **zweryfikowany** Rust

> Status: **Faza 0 ukończona** (spike walidacyjny — patrz [REPORT.md](REPORT.md)) ·
> Plan produktu: [PLAN.md](PLAN.md) · Decyzje: [docs/decisions/](docs/decisions/)

**Idea:** klient wskazuje gorące funkcje swojej biblioteki Python → dostaje ich
implementacje w Rust jako drop-in zamiennik (API 1:1) → równoważność zachowania
jest **udowodniona** differentialowo (replay + generacja + fuzzing), a raport
przed/po (czas, pamięć) jest dowodem wartości. Rust jest środkiem, nie celem.

Zasady projektowe (Z1–Z7): [PLAN.md §1](PLAN.md#1-wizja-produktu).

## Struktura repo

```
PLAN.md                     # plan działania (fazy, kontrakty K1–K8, ryzyka R1–R7)
REPORT.md                   # wyniki fazy 0 (złote reguły, bramka, benchmark)
crates/                     # workspace Rust (std-only — ADR-0004)
  hotport-core/             # manifest + kontrakty + reguła bramki
  hotport-verify/           # silnik równoważności (deep-eq, tolerancja float/ULP)
  hotport-trans/            # mapa typów i stdlib z pułapkami
  hotport-bench/            # statystyki + raport przed/po
  hotport-cli/              # szkielet CLI (profile/translate/verify/bench)
examples/
  spike/                    # Faza 0: port slug/uuid/ipv4 + differential + bench
    core/                   # rdzeń Rust (rlib + cdylib, FFI C-ABI)
    pyo3/                   # binding PyO3 (CI)
    python/hotport_spike/   # shim API 1:1, backendy ref/rust, L1/L2, bramka
    python/hotport_tracer/  # tracer v1: ślad wywołań → manifest 0.1.0 (Faza 1)
    tests/                  # pytest: differential, wstrzyknięte bugi, kanarek
  targets/validators/       # vendor 0.35.0 (MIT) — cel demonstracyjny nr 1
docs/decisions/             # ADR-0001..0005
.github/workflows/ci.yml    # build+test Rust, artefakt .so, differential, bench
```

## Szybki start

```bash
pip install pytest "eth-hash[pycryptodome]"

# silnik differential + bramka + benchmark (działa bez toolchaina Rusta)
python -m pytest examples/spike -q
python examples/spike/python/hotport_spike/runner.py --backend ref
python examples/spike/python/hotport_spike/bench.py

# pełna ścieżka (z toolchainem Rusta): doda backend 'rust' i kolumnę py/rust
cargo build --release -p hotport-spike-core
HOTPORT_IMPL=both python -m pytest examples/spike -q    # tryb kanarka
```

## Jak działa shim (Z4)

```python
import os
os.environ["HOTPORT_IMPL"] = "rust"   # python | rust | both (kanarek)
from hotport_spike import slug, uuid, ipv4   # drop-in dla validators.*
```

Wejścia poza kontraktem rdzenia (np. nie-ASCII) są routowane per-wywołanie do
oryginału (ADR-0005). Tryb `both` porównuje obie implementacje na żywo i rzuca
`CanaryMismatch` przy rozjeździe.
