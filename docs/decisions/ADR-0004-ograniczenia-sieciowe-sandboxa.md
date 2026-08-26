# ADR-0004: Sandbox bez crates.io — std-only + CI-first

* Status: ACCEPTED (2026-08-24)

## Kontekst

Środowisko deweloperskie (sandbox) ma sieć ograniczoną do: github.com,
codeload.github.com, api.github.com, pypi.org, files.pythonhosted.org.
**Niedostępne**: crates.io, static.rust-lang.org, rustup, deb.debian.org,
zasoby GitHub Releases, raw.githubusercontent.com, mirrory crate.

Konsekwencje: brak toolchaina Rusta lokalnie (esp-rs/rust-build hostuje tarbale
tylko w release assets) i brak zależności z crates.io.

## Decyzja

1. **Wszystkie crate'y workspace'u są std-only** (zero zależności) — kompilują
   się w pełni offline. serde/clap/criterion wejdą dopiero, gdy CI potwierdzi
   dostępność (wtedy też ADR rewizja).
2. **Spike ma dwie ścieżki transportu wołające TEN SAM rdzeń**:
   * `ctypes` + C-ABI (`examples/spike/core/src/ffi.rs`) — działa offline,
   * `PyO3` (`examples/spike/pyo3`) — osobny workspace, budowany w CI.
3. **CI-first dla kompilacji Rusta**: GitHub Actions (dtolnay/rust-toolchain)
   buduje, testuje i wrzuca artefakt `.so`, który zasila differential w jobie
   Pythona. Kod Rust pisany w sandboxie jest więc zweryfikowany przez CI
   (trade-off świadomie zaakceptowany w fazie 0).
4. Walidacja semantyki NIE czeka na CI: backend `ref` (wykonywalna specyfikacja
   rdzenia w Pythonie) + differential udowadniają poprawność logiki już offline.

## Konsekwencje

* Każdy PR dostaje zielone/czerwone potwierdzenie kompilacji z CI (nie lokalnie).
* Formatowanie: `cargo fmt` w CI (check), lokalnie ręcznie.
* Trzeba pilnować, aby std-only nie stało się długoterminową kulą u nogi —
  po pierwszym zielonym CI: serde (manifest), clap (CLI), criterion (bench).
