# ADR-0001: Nazwa projektu i licencja

* Status: ACCEPTED (2026-08-24)
* Decydenci: kickoff projektu

## Kontekst

Potrzebna nazwa robocza produktu (PLAN.md — „przyspieszanie bibliotek Python
przez zweryfikowany Rust") oraz licencja open source.

## Decyzja

* **Nazwa: `hotport`** (hot path + port).
  * PyPI: **wolna** (404, sprawdzone 2026-08-24).
  * GitHub: organizacja `hotport` nie istnieje — do zarezerwowania przy publicznym startcie.
  * crates.io: **do zweryfikowania** — sandbox dev nie ma dostępu do crates.io
    (ADR-0004); weryfikacja w pierwszym przebiegu CI lub ręcznie.
  * Crates nazywają się `hotport-*`, moduł Pythona docelowo `hotport`.
* **Licencja: Apache-2.0** (patent grant, kompatybilna z przyszłymi zależnościami).
* Cele demonstracyjne (vendored `validators`, MIT) zostają w `examples/` z pełną
  atrybucją — nie są częścią dystrybucji.

## Alternatywy

* `pyaccel` — **zajęta na PyPI** (200 przy sprawdzaniu).
* `rustport`, `pyrspeed`, `hotrust`, `ferropod`, `pyferrite`, `pyaccel2rs` — wolne
  na PyPI, odrzucone ze względów brzmieniowych/kojarzeniowych.

## Konsekwencje

Przed pierwszą publikacją: rejestracja org GitHub + nazwy na crates.io/PyPI
oraz sprawdzenie znaków towarowych.
