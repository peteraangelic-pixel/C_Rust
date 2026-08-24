# CI — jak włączyć (stan: 2026-08-24)

Sesyjne proxy Areny **podmienia każde uwierzytelnienie do github.com na token
swojej aplikacji GitHub App** (zweryfikowano: nawet losowy token dostaje tę
samą odpowiedź serwera). Aplikacja ma prawo push **contents**, ale **nie ma
uprawnienia `workflows`** — dlatego `.github/workflows/ci.yml` nie mógł pojechać
z gitem (push był odrzucany) i został celowo poza commitem.

## Opcja A (najszybsza, ~2 min): dodaj workflow ręcznie na GitHubie

1. Otwórz branch `arena/01a03364-c-rust` → **Add file → Create new file**
2. Nazwa: `.github/workflows/ci.yml`
3. Wklej treść z lokalnego pliku `.github/workflows/ci.yml`
   (identyczny plik jest w workspace — to ta sama zawartość)
4. Commit → **push do brancha odpala workflow** (`on: push` dla wszystkich
   branchy), więc CI wystartuje natychmiast po dodaniu pliku.

## Opcja B: uprawnienia `workflows` dla aplikacji Areny

Wymaga zmiany po stronie właściciela aplikacji (Arena). Jeśli Arena przy
ponownym łączeniu GitHuba zażąda scope `workflows` — wtedy:
`git rm .github/workflows/ci.yml` z `.gitignore`, zcommituj plik normalnie
i usuń sekcję „non-blocking" z fmt (po pierwszym lokalnym `cargo fmt`).

## Co robi CI (joby)

1. **rust**: `cargo fmt --check` (non-blocking na start) → `cargo test
   --workspace` (std-only) → `cargo build --release -p hotport-spike-core`
   → build bindingu PyO3 (osobny workspace) → artefakt `.so`
2. **python** (needs: rust): pobiera `.so` → pełna suite vendora (895) →
   **differential na PRAWDZIWYM backendzie rust** (usuwa jedyny skip
   w testach) → `runner.py --backend rust` (bramka, exit-code) → bench
   z kolumną py/rust → artefakt z raportami

Uwaga: kod Rust był pisany bez lokalnej kompilacji (ADR-0004) — **pierwszy
przebieg CI to jego pierwsza weryfikacja kompilacyjna**. Jeśli padnie, logi
 Actions pokażą miejsca do poprawki (oczekiwane ryzyko: drobne API PyO3 0.23).
