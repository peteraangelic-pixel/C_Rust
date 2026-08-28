// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0.1 — NIE EDYTOWAĆ
// Helpery semantyki pythona dla wygenerowanych funkcji (patrz translator.py).

/// a // b — semantyka pythona: FLOOR (rust natywnie: trunc)
fn __floordiv(a: i64, b: i64) -> Option<i64> {
    let q = a.checked_div(b)?;
    if (a % b != 0) && ((a < 0) != (b < 0)) {
        q.checked_sub(1)
    } else {
        Some(q)
    }
}

/// -a — checked (-(i64::MIN) przepełnia → routing)
fn __neg(a: i64) -> Option<i64> {
    a.checked_neg()
}

/// a % b — semantyka pythona: znak DZIELNIKA (rust: znak dzielnej)
fn __pymod(a: i64, b: i64) -> Option<i64> {
    let r = a.checked_rem(b)?;
    if r != 0 && ((r < 0) != (b < 0)) {
        r.checked_add(b)
    } else {
        Some(r)
    }
}
