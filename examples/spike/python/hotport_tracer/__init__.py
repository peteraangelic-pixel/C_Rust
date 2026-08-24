"""hotport_tracer — tracer v1 (PLAN.md §Faza 1, komponent [1]).

Obserwuje wywołania funkcji biblioteki-celu pod jej własną suitą testową
(lub dowolnym skryptem) i produkuje:

* **manifest** (`hotport.manifest/0.1.0` — ZAMROŻONY, semver): częstości,
  czasy własne, kształty typów argumentów/wyników, zaobserwowane wyjątki,
  detekcja mutacji argumentów (K4), frakcja ASCII (ADR-0005),
* **replay**: próbki prawdziwych argumentów → wejścia L1 dla differentialu.

Filozofia: niczego nie zgadujemy — wszystko jest zaobserwowane (probe-first).
"""

from .tracer import Tracer, shape_of
from .manifest import SCHEMA_VERSION, build_manifest

__all__ = ["Tracer", "shape_of", "build_manifest", "SCHEMA_VERSION"]
