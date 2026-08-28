# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5345 | 1317 | 784 | 4.06x | 6.82x |
| uuid | 5368 | 1121 | 1183 | 4.79x | 4.54x |
| ipv4 | 12978 | 1655 | 1452 | 7.84x | 8.94x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 281 | 1.00x |
| rust LISCIE (2xFFI) | 2206 | 0.13x |
| rust KLASTER (1xFFI) | 874 | 0.32x |
