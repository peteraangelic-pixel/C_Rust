/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub fn admission(points: f64, lo: f64, hi: f64) -> Option<bool> {
    let in_range: bool = in_band((points), (lo), (hi))?;
    let score_ok: bool = is_score_valid((points))?;
    return Some((in_range) && (score_ok));
}

/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
fn in_band(value: f64, lo: f64, hi: f64) -> Option<bool> {
    return Some(((lo) <= (value)) && ((value) <= (hi)));
}

/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
fn is_score_valid(points: f64) -> Option<bool> {
    let band: i64 = grade((points))?;
    return Some(((band) >= (3)) && ((band) <= (5)));
}

/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
fn grade(points: f64) -> Option<i64> {
    if (points) >= (90.0) {
        return Some(5);
    } else if (points) >= (75.0) {
        return Some(4);
    } else if (points) >= (60.0) {
        return Some(3);
    } else {
        return Some(0);
    }
}
