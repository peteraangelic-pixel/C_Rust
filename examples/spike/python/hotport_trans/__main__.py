"""CLI translatora v0: moduł-cel → wygenerowany Rust + cień + podsumowanie.

    PYTHONPATH=python python -m hotport_trans ../targets/demo_fns.py --out ../generated
"""

import argparse
import os
import sys


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(prog="hotport_trans")
    ap.add_argument("target", help="plik .py z funkcjami w podzbiorze v0")
    ap.add_argument("--entry", default=None,
                    help="tryb KLASTRA (v0.2): przetłumacz region call-graph od tej funkcji")
    ap.add_argument("--out", default=os.path.normpath(os.path.join(here, "..", "..", "generated")),
                    help="katalog wyjściowy (domyślnie examples/spike/generated)")
    args = ap.parse_args(argv)

    from hotport_trans import shadow_module_source, translate_cluster, translate_module

    with open(args.target, encoding="utf-8") as f:
        source = f.read()

    os.makedirs(args.out, exist_ok=True)

    if args.entry:
        cl = translate_cluster(source, args.entry, filename=args.target)
        p = os.path.join(args.out, f"cluster_{cl['entry']}.rs")
        with open(p, "w", encoding="utf-8") as f:
            f.write(cl["rust"])
        shadow_path = os.path.join(args.out, f"shadow_cluster_{cl['entry']}.py")
        with open(shadow_path, "w", encoding="utf-8") as f:
            f.write(shadow_module_source([]) + cl["shadow"])
        print(f"target: {args.target} (KLASTER, entry={cl['entry']})")
        print(f"  czlonkowie: {', '.join(cl['members'])}")
        print(f"  OK -> {p}")
        print(f"  cien klastra: {shadow_path}")
        return 0

    result = translate_module(source, filename=args.target)

    written = []
    for t in result["functions"]:
        p = os.path.join(args.out, f"{t['name']}.rs")
        with open(p, "w", encoding="utf-8") as f:
            f.write(t["rust"])
        written.append(p)

    shadow_path = os.path.join(args.out, "shadow_generated.py")
    with open(shadow_path, "w", encoding="utf-8") as f:
        f.write(shadow_module_source(result["functions"]))

    print(f"target: {args.target}")
    for t in result["functions"]:
        print(f"  OK    {t['name']:10} → {os.path.basename(args.out)}/{t['name']}.rs (+cień)")
    for name, why in result["rejected"]:
        print(f"  SKIP  {name:10} — {why}")
    print(f"cień (wykonywalna specyfikacja): {shadow_path}")
    print(f"przetłumaczone: {len(result['functions'])}, odrzucone: {len(result['rejected'])}")
    return 0 if result["functions"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
