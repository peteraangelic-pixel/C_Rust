"""CLI tracera: uruchom suitę/skrypt klienta pod rejestrowaniem → manifest.

Przykład (cel: validators, suite vendora):

    PYTHONPATH=python:../targets/validators/src python -m hotport_tracer \
        --module validators --names slug uuid ipv4 \
        --pytest ../targets/validators/tests/test_slug.py \
                 ../targets/validators/tests/test_uuid.py \
                 ../targets/validators/tests/test_ip_address.py \
        --out manifest-validators.json
"""

import argparse
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hotport_tracer")
    ap.add_argument("--module", required=True, help="moduł celu, np. validators")
    ap.add_argument("--names", nargs="*", default=None,
                    help="funkcje do wrapowania (domyślnie: wszystkie publiczne)")
    ap.add_argument("--pytest", nargs="*", default=[],
                    help="ścieżki testów pytest do uruchomienia pod rejestrowaniem")
    ap.add_argument("--script", default=None, help="alternatywnie: skrypt .py do exec")
    ap.add_argument("--out", required=True, help="plik manifestu wyjściowego")
    ap.add_argument("--max-samples", type=int, default=25)
    args = ap.parse_args(argv)

    if not args.pytest and not args.script:
        ap.error("podaj --pytest <ścieżki...> lub --script <plik.py>")

    import importlib
    from hotport_tracer import Tracer
    from hotport_tracer.manifest import write_manifest

    module = importlib.import_module(args.module)
    tracer = Tracer(max_samples=args.max_samples)
    tracer.wrap_module(module, names=args.names)

    command = ["pytest", *args.pytest] if args.pytest else ["python", args.script]
    if args.pytest:
        import pytest
        rc = pytest.main(["-q", "-p", "no:cacheprovider", *args.pytest])
        if rc != 0:
            print(f"UWAGA: pytest zwrócił {rc} (manifest i tak powstanie)", file=sys.stderr)
    else:
        with open(args.script, encoding="utf-8") as f:
            code = compile(f.read(), args.script, "exec")
        exec(code, {"__name__": "__main__", "__file__": args.script})  # noqa: S102

    manifest = tracer.manifest(target_module=args.module, command=command)
    tracer.unwrap_all()
    write_manifest(manifest, args.out)

    print(f"manifest: {args.out}  (schema {manifest['schema']})")
    for name, entry in manifest["functions"].items():
        print(f"  {name}: calls={entry['calls']} self_ms={entry['self_ms']:.1f} "
              f"replay={len(entry['replay'])} raises={entry['raises']} "
              f"ascii={entry['ascii_fraction'] if entry['ascii_fraction'] is not None else '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
