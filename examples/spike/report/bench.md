# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5488 | 1278 | 806 | 4.30x | 6.81x |
| uuid | 5428 | 1130 | 1221 | 4.80x | 4.45x |
| ipv4 | 13144 | 1650 | 1450 | 7.96x | 9.07x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 285 | 1.00x |
| rust LISCIE (2xFFI) | 2242 | 0.13x |
| rust KLASTER (1xFFI) | 901 | 0.32x |
