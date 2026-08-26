# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 4163 | 1022 | 622 | 4.07x | 6.69x |
| uuid | 4116 | 869 | 939 | 4.74x | 4.38x |
| ipv4 | 10032 | 1308 | 1127 | 7.67x | 8.90x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 221 | 1.00x |
| rust LISCIE (2xFFI) | 1695 | 0.13x |
| rust KLASTER (1xFFI) | 663 | 0.33x |
