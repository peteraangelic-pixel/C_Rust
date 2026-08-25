//! KLASTER v0.2 [REVIEW pkt 8-9] — kod WYGENEROWANY automatycznie przez
//! hotport_trans (translate_cluster z examples/targets/demo_cluster.py,
//! entry=admission). JEDNO przejście FFI na cały region; wywołania
//! wewnętrzne (in_band/grade/is_score_valid) są w Rust darmowe.
//!
//! Golden: python-side test (tests/test_cluster.py) weryfikuje, że ten plik
//! zawiera dokładnie treść examples/spike/generated/cluster_admission.rs.

/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub fn admission(points: f64, lo: f64, hi: f64) -> Option<bool> {
    let in_range: bool = in_band(points, lo, hi)?;
    let score_ok: bool = is_score_valid(points)?;
    return Some((in_range) && (score_ok));
}

/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub(crate) fn in_band(value: f64, lo: f64, hi: f64) -> Option<bool> {
    return Some(((lo) <= (value)) && ((value) <= (hi)));
}

/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub(crate) fn is_score_valid(points: f64) -> Option<bool> {
    let band: i64 = grade(points)?;
    return Some(((band) >= (3)) && ((band) <= (5)));
}

/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub(crate) fn grade(points: f64) -> Option<i64> {
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

#[cfg(test)]
mod tests {
    #[test]
    fn klaster_semantyka() {
        assert_eq!(super::admission(80.0, 0.0, 100.0), Some(true));
        assert_eq!(super::admission(50.0, 0.0, 100.0), Some(false)); // banda 0
        assert_eq!(super::admission(59.9, 0.0, 100.0), Some(false));
        assert_eq!(super::admission(75.0, 0.0, 100.0), Some(true));
        assert_eq!(super::admission(f64::NAN, 0.0, 100.0), Some(false));
        assert_eq!(super::admission(80.0, 90.0, 100.0), Some(false)); // poza zakresem
        assert_eq!(super::grade(90.0), Some(5));
        assert_eq!(super::grade(89.999), Some(4));
        assert_eq!(super::in_band(1.0, 0.0, 2.0), Some(true));
    }
}
