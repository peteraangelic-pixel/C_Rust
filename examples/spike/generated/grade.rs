/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub fn grade(points: f64) -> Option<i64> {
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
