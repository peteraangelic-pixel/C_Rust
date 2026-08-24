# ADR-0003: LLM wyłączony w v1 — deterministycznie najpierw

* Status: ACCEPTED (2026-08-24)

## Kontekst

PLAN.md Z3: rdzeń deterministyczny, LLM jako generator hipotez. Pytanie: czy
warstwa LLM wchodzi do MVP?

## Decyzja

**v1 bez LLM.** Translator = reguły + mapa stdlib (hotport-trans). Interfejs
`Translator` jest zaprojektowany pod wymienne backendy; LLM dojdzie jako plugin
w v2, zawsze ZA bramką weryfikacji (Z2: LLM nigdy nie jest źródłem prawdy).

## Uzasadnienie

1. **Powtarzalność CI** — brak niedeterminizmu w pipeline; każdy artefakt ma
   równoważny dowód z deterministicznego przebiegu.
2. **Zgodność enterprise** — klienci z kodem zamkniętym często wyłączają chmurę;
   produkt musi działać no-cloud (Z6).
3. **Koszt** — faza 0 pokazała, że samo dopasowanie semantyki (złote reguły)
   daje ogromną wartość bez AI; LLM nie rozwiąże pułapek z REPORT.md lepiej
   niż zakodowane reguły + differential.
4. **Moat** — weryfikacja, nie generacja, jest produktem.

## Powrót do tematu

v2: `LlmTranslator` implementujący `Translator` (cache, temperature 0),
włączany per-funkcja flagą w manifeście; wynik zawsze przez L1+L2+bramkę.
