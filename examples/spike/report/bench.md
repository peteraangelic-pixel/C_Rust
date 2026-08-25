# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 6094 | 1179 | 874 | 5.17x | 6.97x |
| uuid | 6110 | 1055 | 1210 | 5.79x | 5.05x |
| ipv4 | 17239 | 1846 | 1515 | 9.34x | 11.38x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 290 | 1.00x |
| rust LISCIE (2xFFI) | 2290 | 0.13x |
| rust KLASTER (1xFFI) | 926 | 0.31x |
