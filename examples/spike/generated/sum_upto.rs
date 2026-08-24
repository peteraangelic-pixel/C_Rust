/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub fn sum_upto(n: i64) -> Option<i64> {
    let mut total: i64 = 0;
    for i in (1)..((n).checked_add(1)?) {
        total = (total).checked_add(i)?;
    }
    return Some(total);
}
