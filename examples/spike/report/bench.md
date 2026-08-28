# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 6028 | 1190 | 846 | 5.07x | 7.13x |
| uuid | 6186 | 1086 | 1215 | 5.70x | 5.09x |
| ipv4 | 17375 | 1795 | 1477 | 9.68x | 11.76x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 282 | 1.00x |
| rust LISCIE (2xFFI) | 2216 | 0.13x |
| rust KLASTER (1xFFI) | 903 | 0.31x |
