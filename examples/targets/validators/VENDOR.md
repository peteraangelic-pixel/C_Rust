# Vendor: validators 0.35.0

* Źródło: https://github.com/python-validators/validators
* Commit: `70de324` (master, 2026-08-24)
* Licencja: MIT (LICENSE.txt) — kopiowanie zgodne z licencją
* Usunięte przy vendoringu: `.git/`, `docs/`, `package/`, `.github/`, `pdm.lock`, `mkdocs.yaml`, `MANIFEST.in`

## Dlaczego

Cel demonstracyjny nr 1 (PLAN.md §2): mała, czysta biblioteka Python z dobrą suitą
testów — idealna do badań differential (faza 0) i pierwszych tłumaczeń (faza 2).

## Uruchomienie suite

```bash
pip install pytest "eth-hash[pycryptodome]"   # eth-hash = opcjonalne crypto-eth
PYTHONPATH=src python -m pytest tests/ -q
# 895 passed (2026-08-24, Python 3.11)
```

Bez `eth-hash` 17 testów `eth_address` pada (opcjonalna zależność) — znane,
niezwiązane z naszymi zmianami. **Nie modyfikujemy kodu vendora**; wszystkie
eksperymenty żyją w `examples/spike/`.
