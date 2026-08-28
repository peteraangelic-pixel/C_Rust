# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5489 | 1304 | 797 | 4.21x | 6.89x |
| uuid | 5336 | 1119 | 1201 | 4.77x | 4.44x |
| ipv4 | 13188 | 1682 | 1443 | 7.84x | 9.14x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 287 | 1.00x |
| rust LISCIE (2xFFI) | 2214 | 0.13x |
| rust KLASTER (1xFFI) | 871 | 0.33x |
