"""hotport_trans v0 — deterministyczny translator podzbioru Pythona → Rust.

v0 to PROTOTYP po stronie Pythona (jak ref-backend w fazie 0): reguły są
wytłumaczalne i wykonywalne (cień), kod Rust wylatuje jako tekst i zostanie
podpięty do kompilacji w CI. Docelowy rdzeń translacji to crate `hotport-trans`
(w workspace) — przeniesienie reguł v0 tam nastąpi po pierwszym zielonym CI.
"""

from .translator import (
    SHADOW_PRELUDE,
    UnsupportedNode,
    shadow_module_source,
    translate_cluster,
    translate_module,
)

__all__ = [
    "translate_module",
    "translate_cluster",
    "shadow_module_source",
    "UnsupportedNode",
    "SHADOW_PRELUDE",
]
