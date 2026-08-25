# Benchmark równoległy: ipv4 × 100000 elementów (median, 5 powtórzeń)

| wariant | czas [ms] | ns/element | vs list-comp | vs ProcessPool |
|---|---|---|---|---|
| python list-comp (GIL, 1 rdzeń) | 1011.5 | 10115 | 1.00x | 0.54x |
| python ProcessPool×2 | 546.7 | 5467 | 1.85x | 1.00x |
