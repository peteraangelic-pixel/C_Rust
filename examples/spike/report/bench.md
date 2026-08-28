# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5853 | 1200 | 867 | 4.88x | 6.75x |
| uuid | 6073 | 1080 | 1204 | 5.62x | 5.05x |
| ipv4 | 17147 | 1782 | 1533 | 9.62x | 11.19x |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).

## Klaster admission (median ns/op, n=30000)

| wariant | ns/op | vs python |
|---|---|---|
| python (lancuch) | 288 | 1.00x |
| rust LISCIE (2xFFI) | 2251 | 0.13x |
| rust KLASTER (1xFFI) | 894 | 0.32x |
