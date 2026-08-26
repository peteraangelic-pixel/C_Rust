# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5429 | 1080 | 788 | 5.03x | 6.89x |
| uuid | 5317 | 1095 | 1197 | 4.86x | 4.44x |
| ipv4 | 12976 | 1664 | 1446 | 7.80x | 8.97x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 281 | 1.00x |
| rust LISCIE (2xFFI) | 2240 | 0.13x |
| rust KLASTER (1xFFI) | 857 | 0.33x |
