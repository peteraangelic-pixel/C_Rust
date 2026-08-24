"""Translator deterministyczny v0 — podzbiór Pythona → Rust (+ cień Python).

Zasady (PLAN.md Z3, ADR-0003 — bez LLM):
* wejście: funkcja z adnotacjami typów, napisana w podzbiorze v0,
* wyjście A: **kod Rust** (tekst; kompilacja w CI — ADR-0004),
* wyjście B: **cień** — wygenerowany Python O TYCH SAMYCH regułach, z guardami
  semantyki Rust (i64 checked, brak truthiness), który DA SIĘ differentialowo
  zweryfikować już dziś wobec oryginału (metodologia ref-backend z fazy 0).

Każda reguła ma swój odpowiednik po obu stronach — cokolwiek innego niż
1:1 to bug translatora i MUSI wyjść w differentialu.
"""

import ast
import textwrap

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1

# ------------------------------------------------------------------ podzbiór

_BIN_INT = {"Add": "checked_add", "Sub": "checked_sub", "Mult": "checked_mul"}
_BIN_FLOAT = {"Add": "+", "Sub": "-", "Mult": "*", "Div": "/"}
_CMP = {"Lt": "<", "LtE": "<=", "Gt": ">", "GtE": ">=", "Eq": "==", "NotEq": "!="}


class UnsupportedNode(Exception):
    """Węzeł AST poza podzbiorem v0 — powód trafia do raportu (Z5)."""

    def __init__(self, fn, node, why):
        self.fn, self.why = fn, why
        super().__init__(
            f"{fn}: {type(node).__name__} (linia {getattr(node, 'lineno', '?')}) — {why}"
        )


class TranslationError(Exception):
    pass


_TYPE_MAP = {"int": "i64", "float": "f64", "str": "&str", "bool": "bool"}


def _ann(node, fn):
    if isinstance(node, ast.Name) and node.id in _TYPE_MAP:
        return _TYPE_MAP[node.id]
    raise UnsupportedNode(fn, node, f"adnotacja {ast.dump(node)[:40]} poza v0 (dozwolone: int/float/str/bool)")


def _returns_always(body):
    for st in body:
        if isinstance(st, ast.Return):
            return True
        if isinstance(st, ast.If) and st.orelse and _returns_always(st.body) and _returns_always(st.orelse):
            return True
    return False


class _FnTranslator:
    def __init__(self, fndef):
        self.fn = fndef.name
        self.fndef = fndef
        self.vars = {}  # nazwa -> typ ("i64"/"f64"/...)
        self.args = []  # [(name, ty)]
        self.ret = _ann(fndef.returns, self.fn) if fndef.returns else None
        if self.ret is None:
            raise UnsupportedNode(self.fn, fndef, "brak adnotacji zwracanego typu (wymagana w v0)")
        # nazwy przypisywane więcej niż raz → wymagają `mut` w deklaracji
        from collections import Counter
        counts = Counter(
            t.id
            for st in ast.walk(ast.Module(body=fndef.body, type_ignores=[]))
            if isinstance(st, ast.Assign)
            for t in st.targets
            if isinstance(t, ast.Name)
        )
        self.mutable = {n for n, k in counts.items() if k > 1}

    # ---------------------------------------------------------- wyrażenia

    def expr(self, e):
        """→ (rust, py, typ). Każda gałąź utrzymuje parę 1:1."""
        fn = self.fn
        if isinstance(e, ast.Constant):
            if isinstance(e.value, bool):
                return ("true" if e.value else "false", "True" if e.value else "False", "bool")
            if isinstance(e.value, int):
                if not (I64_MIN <= e.value <= I64_MAX):
                    raise UnsupportedNode(fn, e, f"literał int {e.value} poza i64 (K3)")
                return (str(e.value), str(e.value), "i64")
            if isinstance(e.value, float):
                return (repr(e.value), repr(e.value), "f64")
            if isinstance(e.value, str):
                r = '"' + e.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
                return (r, repr(e.value), "&str")
            raise UnsupportedNode(fn, e, f"literał {type(e.value).__name__} poza v0")
        if isinstance(e, ast.Name):
            ty = self.vars.get(e.id)
            if ty is None:
                raise UnsupportedNode(fn, e, f"nieznana zmienna {e.id!r} (brak deklaracji w v0)")
            return (e.id, e.id, ty)
        if isinstance(e, ast.BinOp):
            op = type(e.op).__name__
            l, lp, lt = self.expr(e.left)
            r, rp, rt = self.expr(e.right)
            if lt == "i64" and rt == "i64":
                if op not in _BIN_INT:
                    raise UnsupportedNode(fn, e, f"operator {op} na int poza v0 (// % ** → patrz dokumentacja pułapek)")
                rust = f"({l}).{_BIN_INT[op]}({r})?"
                return (rust, f"_bin('{op[0].lower()}', {lp}, {rp})", "i64")
            # dowolna strona float → f64 (int koercja jawna; mixed ==/porównania odrzucane niżej)
            if "f64" in (lt, rt) and lt in ("i64", "f64") and rt in ("i64", "f64"):
                opf = _BIN_FLOAT.get(op)
                if opf is None:
                    raise UnsupportedNode(fn, e, f"operator {op} na float poza v0")
                lr = f"(({l}) as f64)" if lt == "i64" else f"({l})"
                rr = f"(({r}) as f64)" if rt == "i64" else f"({r})"
                # cień MUSI symulować koercję rustową (as f64 = zaokrąglenie do najbliższej
                # wartości f64) — dlatego float() po stronie pythonowej inta. Oracle python
                # liczy mixed dokładnie, więc różnica na wielkich intach WYJDZIE w differentialu (K2).
                lpr = f"float({lp})" if lt == "i64" else f"({lp})"
                rpr = f"float({rp})" if rt == "i64" else f"({rp})"
                return (f"{lr} {opf} {rr}", f"({lpr} {opf} {rpr})", "f64")
            raise UnsupportedNode(fn, e, f"BinOp {lt} {op} {rt} poza v0 (tylko i64×i64 / f64)")
        if isinstance(e, ast.UnaryOp):
            if isinstance(e.op, ast.Not):
                v, vp, vt = self.expr(e.operand)
                if vt != "bool":
                    raise UnsupportedNode(fn, e, "not na nie-bool (truthiness poza v0)")
                return (f"!({v})", f"(not {vp})", "bool")
            if isinstance(e.op, ast.USub):
                v, vp, vt = self.expr(e.operand)
                if vt == "f64":
                    return (f"-({v})", f"-({vp})", "f64")
                raise UnsupportedNode(fn, e, "unarne minus na int poza v0 (checked_neg — v0.1)")
            raise UnsupportedNode(fn, e, "UnaryOp poza v0")
        if isinstance(e, ast.BoolOp):
            op = "&&" if isinstance(e.op, ast.And) else "||"
            pop = " and " if op == "&&" else " or "
            parts, pparts = [], []
            for v in e.values:
                r, p, t = self.expr(v)
                if t != "bool":
                    raise UnsupportedNode(fn, e, f"BoolOp na {t} (truthiness poza v0 — jawny warunek bool wymagany)")
                parts.append(f"({r})")
                pparts.append(f"({p})")
            return (f" {op} ".join(parts), pop.join(pparts), "bool")
        if isinstance(e, ast.Compare):
            left, leftp, leftt = self.expr(e.left)
            leftn = e.left  # potrzebny node do reguły literału poniżej
            rs, rps = [], []
            cur, curp, curt, curn = left, leftp, leftt, leftn
            for op, comp in zip(e.ops, e.comparators):
                r, rp, rt = self.expr(comp)
                o = _CMP.get(type(op).__name__)
                if o is None:
                    raise UnsupportedNode(fn, e, f"porównanie {type(op).__name__} poza v0 (is None → v0.1)")
                if curt == rt and curt in ("i64", "f64", "bool", "&str"):
                    pass  # jednotypowe — bez zmian
                elif {curt, rt} == {"i64", "f64"}:
                    # mixed DOZWOLONE tylko gdy strona int jest LITERAŁEM ≤2^53
                    # (dokładnie reprezentowalny w f64; python porównuje wartościowo,
                    #  więc wynik identyczny). Int zmienna → odrzucamy (koercja f64
                    # dużych intów gubi precyzję — pułapka K2).
                    node = curn if curt == "i64" else comp
                    if not (isinstance(node, ast.Constant) and isinstance(node.value, int)
                            and abs(node.value) <= 2**53):
                        raise UnsupportedNode(
                            fn, e,
                            "porównanie mixed int/float dozwolone w v0 tylko dla literału int ≤2^53 "
                            "(python porównuje wartościowo; koercja f64 gubi precyzję — K2)",
                        )
                    if curt == "i64":
                        cur = repr(float(cur))  # 90 → 90.0 (rust)
                    else:
                        r = repr(float(r))
                else:
                    raise UnsupportedNode(fn, e, f"porównanie {curt} {o} {rt} poza v0")
                rs.append(f"({cur}) {o} ({r})")
                rps.append(f"({curp}) {o} ({rp})")
                cur, curp, curt, curn = r, rp, rt, comp
            return (" && ".join(rs), " and ".join(rps) if len(rs) > 1 else rps[0], "bool")
        if isinstance(e, ast.Call):
            return self.call(e)
        raise UnsupportedNode(fn, e, "wyrażenie poza podzbiorem v0")

    def call(self, e):
        fn = self.fn
        # len(s)
        if isinstance(e.func, ast.Name) and e.func.id == "len" and len(e.args) == 1:
            v, vp, vt = self.expr(e.args[0])
            if vt != "&str":
                raise UnsupportedNode(fn, e, f"len() na {vt} — tylko str w v0")
            # PUŁAPKA: python len(str) = pkt kodowe; rust s.len() = BAJTY → chars().count()
            return (f"({v}).chars().count()", f"len({vp})", "i64")
        # abs/min/max — tylko float w v0
        if isinstance(e.func, ast.Name) and e.func.id in ("abs", "min", "max"):
            args = [self.expr(a) for a in e.args]
            if not (1 <= len(args) <= 2):
                raise UnsupportedNode(fn, e, "abs/min/max: 1-2 argumenty w v0")
            if any(t != "f64" for _, _, t in args):
                raise UnsupportedNode(fn, e, "abs/min/max na nie-float poza v0")
            codes = [c for c, _, _ in args]
            pcodes = [p for _, p, _ in args]
            if e.func.id == "abs":
                return (f"({codes[0]}).abs()", f"abs({pcodes[0]})", "f64")
            m = "min" if e.func.id == "min" else "max"
            return (f"({codes[0]}).{m}({codes[1]})", f"{m}({pcodes[0]}, {pcodes[1]})", "f64")
        # metody str: startswith/endswith → starts_with/ends_with (mapowanie nazw!)
        _STR_METHODS = {"startswith": "starts_with", "endswith": "ends_with"}
        if isinstance(e.func, ast.Attribute) and e.func.attr in _STR_METHODS:
            base, basep, bt = self.expr(e.func.value)
            if bt != "&str" or len(e.args) != 1:
                raise UnsupportedNode(fn, e, f".{e.func.attr} w v0: tylko str × 1 arg")
            a, ap, at = self.expr(e.args[0])
            if at != "&str":
                raise UnsupportedNode(fn, e, f".{e.func.attr}({at}) — tylko str")
            m = _STR_METHODS[e.func.attr]
            return (f"({base}).{m}({a})", f"{basep}.{e.func.attr}({ap})", "bool")
        raise UnsupportedNode(fn, e, f"wywołanie poza whitelistą v0: {ast.dump(e.func)[:50]}")

    # ---------------------------------------------------------- instrukcje

    def stmts(self, body, indent, rust_out, py_out, py_indent):
        pad, ppad = "    " * indent, "    " * py_indent
        for st in body:
            if isinstance(st, ast.Return):
                v, vp, vt = self.expr(st.value) if st.value else (None, None, None)
                if vt != self.ret:
                    raise UnsupportedNode(self.fn, st, f"return {vt}, deklarowano {self.ret}")
                rust_out.append(f"{pad}return Some({v});")
                py_out.append(f"{ppad}return {vp};")
            elif isinstance(st, ast.Assign):
                if len(st.targets) != 1 or not isinstance(st.targets[0], ast.Name):
                    raise UnsupportedNode(self.fn, st, "Assign: pojedyncza nazwa w v0")
                name = st.targets[0].id
                v, vp, vt = self.expr(st.value)
                if name in self.vars:
                    # PONOWNE przypisanie: typ musi się zgadzać (v0: stała typizacja),
                    # emitujemy PRZYPISANIE (nie let — pułapka znaleziona w v0: pierwotny
                    # emitter generował `let`, co w Rust daje shadowing zamiast update'u)
                    if vt != self.vars[name]:
                        raise UnsupportedNode(self.fn, st, f"zmienna {name} zmienia typ {self.vars[name]}→{vt} (v0: zabronione)")
                    rust_out.append(f"{pad}{name} = {v};")
                else:
                    self.vars[name] = vt
                    mut = "mut " if name in self.mutable else ""
                    rust_out.append(f"{pad}let {mut}{name}: {_rs_ty(vt)} = {v};")
                py_out.append(f"{ppad}{name} = {vp};")
            elif isinstance(st, ast.If):
                t, tp, tt = self.expr(st.test)
                if tt != "bool":
                    raise UnsupportedNode(self.fn, st, f"if-test {tt} (truthiness poza v0)")
                rust_out.append(f"{pad}if {t} {{")
                py_out.append(f"{ppad}if {tp}:")
                self.stmts(st.body, indent + 1, rust_out, py_out, py_indent + 1)
                if st.orelse:
                    # elif = zagnieżdżony If — rozwiń dla ładnego Rusta
                    if len(st.orelse) == 1 and isinstance(st.orelse[0], ast.If):
                        self._elif(st.orelse[0], indent, rust_out, py_out, py_indent)
                    else:
                        rust_out.append(f"{pad}}} else {{")
                        py_out.append(f"{ppad}else:")
                        self.stmts(st.orelse, indent + 1, rust_out, py_out, py_indent + 1)
                        rust_out.append(f"{pad}}}")
                else:
                    rust_out.append(f"{pad}}}")
            elif isinstance(st, ast.For):
                if (not isinstance(st.iter, ast.Call) or not isinstance(st.iter.func, ast.Name)
                        or st.iter.func.id != "range" or not 1 <= len(st.iter.args) <= 2):
                    raise UnsupportedNode(self.fn, st, "For: tylko range(a, b) / range(n) w v0")
                tgt = st.target
                if not isinstance(tgt, ast.Name):
                    raise UnsupportedNode(self.fn, st, "For-target: pojedyncza nazwa")
                rng = [self.expr(a) for a in st.iter.args]
                if any(t != "i64" for _, _, t in rng):
                    raise UnsupportedNode(self.fn, st, "range() na nie-int")
                lo = ("0", "0") if len(rng) == 1 else (rng[0][0], rng[0][1])
                hi = (rng[-1][0], rng[-1][1])
                self.vars[tgt.id] = "i64"
                rust_out.append(f"{pad}for {tgt.id} in ({lo[0]})..({hi[0]}) {{")
                py_out.append(f"{ppad}for {tgt.id} in range({lo[1]}, {hi[1]}):")
                self.stmts(st.body, indent + 1, rust_out, py_out, py_indent + 1)
                rust_out.append(f"{pad}}}")
            else:
                raise UnsupportedNode(self.fn, st, f"instrukcja {type(st).__name__} poza v0")

    def _elif(self, ifnode, indent, rust_out, py_out, py_indent):
        pad, ppad = "    " * indent, "    " * py_indent
        t, tp, tt = self.expr(ifnode.test)
        rust_out.append(f"{pad}}} else if {t} {{")
        py_out.append(f"{ppad}elif {tp}:")
        self.stmts(ifnode.body, indent + 1, rust_out, py_out, py_indent + 1)
        if ifnode.orelse:
            if len(ifnode.orelse) == 1 and isinstance(ifnode.orelse[0], ast.If):
                self._elif(ifnode.orelse[0], indent, rust_out, py_out, py_indent)
            else:
                rust_out.append(f"{pad}}} else {{")
                py_out.append(f"{ppad}else:")
                self.stmts(ifnode.orelse, indent + 1, rust_out, py_out, py_indent + 1)
                rust_out.append(f"{pad}}}")
        else:
            rust_out.append(f"{pad}}}")

    # ---------------------------------------------------------- całość

    def translate(self):
        f = self.fndef
        for a in f.args.args:
            if a.annotation is None:
                raise UnsupportedNode(self.fn, a, "argument bez adnotacji typu (wymagana w v0)")
            ty = _ann(a.annotation, self.fn)
            self.args.append((a.arg, ty))
            self.vars[a.arg] = ty
        if f.args.kwonlyargs or f.args.vararg or f.args.kwarg or f.args.defaults or f.args.posonlyargs:
            raise UnsupportedNode(self.fn, f, "v0: tylko pozycyjne argumenty bez defaultów")

        body = f.body
        # docstring to ast.Expr — pomijamy (to nie instrukcja wykonawcza)
        if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]

        rust, py = [], []
        self.stmts(body, 1, rust, py, 1)
        if not _returns_always(body):
            raise UnsupportedNode(self.fn, f, "nie wszystkie ścieżki возвращają (wymagane w v0)")

        sig_r = ", ".join(f"{n}: {_rs_ty(t)}" for n, t in self.args)
        head_r = f"/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ\npub fn {self.fn}({sig_r}) -> Option<{_rs_ty(self.ret)}> {{"
        tail_r = "    Some(<ostatnie wyrażenie jest w return powyżej>)\n}"  # nieistotne — return-y są wyczerpujące
        body_r = "\n".join(rust)
        # usuń atrapę: wszystkie ścieżki mają return — wystarczy pusty fallback na potrzeby kompilatora
        code_rust = f"{head_r}\n{body_r}\n}}\n"

        guards = [f"        if not ({I64_MIN} <= {n} <= {I64_MAX}): raise _Out()" for n, t in self.args if t == "i64"]
        sig_p = ", ".join(n for n, _ in self.args)
        code_py = (
            f"def {self.fn}({sig_p}):\n"
            f"    try:\n"
            + ("\n".join(guards) + "\n" if guards else "")
            + "\n".join("    " + l for l in py) + "\n"
            f"    except _Out:\n        return None\n"
        )
        return {"name": self.fn, "rust": code_rust, "shadow": code_py}


def _rs_ty(t):
    return {"i64": "i64", "f64": "f64", "bool": "bool", "&str": "&str"}[t]


SHADOW_PRELUDE = f'''# WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
# Cień = te same reguły translacji co kod Rust, wykonywalne w Pythonie:
# * int: arytmetyka _bin z kontrolą zakresu i64 (K3) — przekroczenie → _Out → None (routing),
# * brak truthiness — warunki jawnie bool,
_I64_MIN = {I64_MIN}
_I64_MAX = {I64_MAX}


class _Out(Exception):
    pass


def _chk(r):
    if not (_I64_MIN <= r <= _I64_MAX):
        raise _Out()
    return r


def _bin(op, a, b):
    if op == 'a':
        return _chk(a + b)
    if op == 's':
        return _chk(a - b)
    if op == 'm':
        return _chk(a * b)
    raise AssertionError(op)

'''


def translate_module(source, filename="<source>"):
    """→ {"functions": [Translation], "rejected": [(fn, powód)]}."""
    tree = ast.parse(source, filename=filename)
    out, rejected = [], []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        try:
            out.append(_FnTranslator(node).translate())
        except UnsupportedNode as e:
            rejected.append((node.name, str(e)))
    return {"functions": out, "rejected": rejected}


def shadow_module_source(translations):
    parts = [SHADOW_PRELUDE]
    for t in translations:
        parts.append("\n\n" + t["shadow"])
    return "".join(parts)
