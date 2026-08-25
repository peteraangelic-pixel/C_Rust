# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5430 | 1286 | 816 | 4.22x | 6.65x |
| uuid | 5297 | 1103 | 1227 | 4.80x | 4.32x |
| ipv4 | 12952 | 1682 | 1512 | 7.70x | 8.56x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 281 | 1.00x |
| rust LISCIE (2xFFI) | 2189 | 0.13x |
| rust KLASTER (1xFFI) | 870 | 0.32x |
