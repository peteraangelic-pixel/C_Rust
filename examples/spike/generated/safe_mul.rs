/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub fn safe_mul(a: i64, b: i64) -> Option<i64> {
    return Some((a).checked_mul(b)?);
}
