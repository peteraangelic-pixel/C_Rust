# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5952 | 1206 | 850 | 4.93x | 7.00x |
| uuid | 5955 | 1054 | 1269 | 5.65x | 4.69x |
| ipv4 | 17026 | 1750 | 1434 | 9.73x | 11.88x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 286 | 1.00x |
| rust LISCIE (2xFFI) | 2289 | 0.12x |
| rust KLASTER (1xFFI) | 895 | 0.32x |
