# Benchmark spike'a (median ns/op, n=30000 wywołań, … unikalnych wejść)

| fn | python (validators) | ref (spec, python) | rust (ctypes) | py/ref | py/rust |
|---|---|---|---|---|---|
| slug | 5397 | 1198 | — | 4.50x | — |
| uuid | 5480 | 1048 | — | 5.23x | — |
| ipv4 | 16121 | 1520 | — | 10.60x | — |

Uwaga: 'ref' to PYTHONOWA specyfikacja rdzenia (logika bez re/ipaddress/uuid),
'rust' = te same funkcje przez ctypes (FII overhead ~0.3–1 µs/wywołanie —
to właśnie ryzyko R2 z PLAN.md; docelowo PyO3 + tłumaczenie całych klastrów).
