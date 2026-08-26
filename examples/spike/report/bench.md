# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5934 | 1180 | 846 | 5.03x | 7.01x |
| uuid | 5942 | 1082 | 1184 | 5.49x | 5.02x |
| ipv4 | 16732 | 1745 | 1486 | 9.59x | 11.26x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 291 | 1.00x |
| rust LISCIE (2xFFI) | 2251 | 0.13x |
| rust KLASTER (1xFFI) | 890 | 0.33x |
