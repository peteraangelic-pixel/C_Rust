//! Silnik weryfikacji równoważności — rdzeń moatu (PLAN.md §4, K1–K8).
//!
//! Model wartości pokrywa wyniki typowych predykatów/funkcji bibliotecznych;
//! porównanie głębokie ze śledzeniem ścieżki rozbieżności i polityką float
//! (tolerancja relatywna + bezwzględna + ULP). Std-only (ADR-0004).

use std::fmt;

/// Polityka porównania liczb zmiennoprzecinkowych (kontrakt K2).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FloatPolicy {
    pub rel_tol: f64,
    pub abs_tol: f64,
    pub max_ulp: u64,
    /// Czy `-0.0 == 0.0` traktować jako równe (domyślnie tak, jak w Pythonie).
    pub signed_zero_equal: bool,
}

impl Default for FloatPolicy {
    fn default() -> Self {
        // Domyślnie: ŚCISŁE porównanie bitowe; tolerancje włącza się per funkcja.
        Self {
            rel_tol: 0.0,
            abs_tol: 0.0,
            max_ulp: 0,
            signed_zero_equal: true,
        }
    }
}

/// Wartość wynikowa funkcji w neutralnym modelu (odpowiednik JSON + bytes).
#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i128),
    Float(f64),
    Str(String),
    Bytes(Vec<u8>),
    List(Vec<Value>),
    /// Dict z zachowaniem kolejności wstawiania (kontrakt K8).
    Dict(Vec<(Value, Value)>),
}

/// Wynik porównania pary wartości.
#[derive(Debug, Clone, PartialEq)]
pub enum Diff {
    Equal,
    FloatWithinTolerance {
        left: f64,
        right: f64,
        ulp: u64,
    },
    NotEqual {
        path: String,
        left: Value,
        right: Value,
    },
}

fn ulp_diff(a: f64, b: f64) -> u64 {
    // Trik Wylla/Dawsona: mapowanie bitów na przestrzeń monotoniczną,
    // różnica ULP jest wtedy zwykłą różnicą całkowitoliczbową.
    let la = a.to_bits() as i64;
    let lb = b.to_bits() as i64;
    let la = if la < 0 {
        0x8000_0000_0000_0000u64.wrapping_sub(la as u64) as i64
    } else {
        la
    };
    let lb = if lb < 0 {
        0x8000_0000_0000_0000u64.wrapping_sub(lb as u64) as i64
    } else {
        lb
    };
    (la - lb).unsigned_abs()
}

/// None = na pewno nierówne; Some(d) = wynik (Equal lub tolerancja).
fn eq_float(a: f64, b: f64, p: &FloatPolicy) -> Option<Diff> {
    if a.is_nan() && b.is_nan() {
        return Some(Diff::Equal); // zgodnie z pythonowym math.isnan w testach
    }
    if a.is_nan() || b.is_nan() {
        return None;
    }
    if a == b {
        let same_sign = a.is_sign_positive() == b.is_sign_positive();
        if a == 0.0 && !same_sign && !p.signed_zero_equal {
            return None;
        }
        return Some(Diff::Equal);
    }
    let ulp = ulp_diff(a, b);
    let close = (a - b).abs() <= p.abs_tol
        || (a - b).abs() <= p.rel_tol * a.abs().max(b.abs())
        || ulp <= p.max_ulp;
    if close {
        Some(Diff::FloatWithinTolerance {
            left: a,
            right: b,
            ulp,
        })
    } else {
        None
    }
}

fn push_path(prefix: &str, key: &str) -> String {
    if prefix.is_empty() {
        key.to_string()
    } else {
        format!("{prefix}.{key}")
    }
}

fn mismatch(a: &Value, b: &Value, path: &str) -> Diff {
    Diff::NotEqual {
        path: path.to_string(),
        left: a.clone(),
        right: b.clone(),
    }
}

fn eq_value(a: &Value, b: &Value, p: &FloatPolicy, path: &str) -> Diff {
    match (a, b) {
        (Value::Float(x), Value::Float(y)) => match eq_float(*x, *y, p) {
            Some(d) => d,
            None => mismatch(a, b, path),
        },
        (Value::Int(x), Value::Int(y)) if x == y => Diff::Equal,
        (Value::Bool(x), Value::Bool(y)) if x == y => Diff::Equal,
        (Value::Null, Value::Null) => Diff::Equal,
        (Value::Str(x), Value::Str(y)) if x == y => Diff::Equal,
        (Value::Bytes(x), Value::Bytes(y)) if x == y => Diff::Equal,
        (Value::List(x), Value::List(y)) => {
            if x.len() != y.len() {
                return mismatch(a, b, &push_path(path, "len"));
            }
            for (i, (xi, yi)) in x.iter().zip(y.iter()).enumerate() {
                let d = eq_value(xi, yi, p, &push_path(path, &format!("[{i}]")));
                if !matches!(d, Diff::Equal) {
                    return d;
                }
            }
            Diff::Equal
        }
        (Value::Dict(x), Value::Dict(y)) => {
            if x.len() != y.len() {
                return mismatch(a, b, &push_path(path, "len"));
            }
            for ((xk, xv), (yk, yv)) in x.iter().zip(y.iter()) {
                let kd = eq_value(xk, yk, p, &push_path(path, "key"));
                if !matches!(kd, Diff::Equal) {
                    return kd;
                }
                let key_label = match xk {
                    Value::Str(s) => s.clone(),
                    _ => "val".to_string(),
                };
                let vd = eq_value(xv, yv, p, &push_path(path, &key_label));
                if !matches!(vd, Diff::Equal) {
                    return vd;
                }
            }
            Diff::Equal
        }
        _ => mismatch(a, b, path),
    }
}

/// Porównaj dwie wartości wg polityki. Ścieżka pusta = korzeń.
pub fn deep_eq(a: &Value, b: &Value, policy: &FloatPolicy) -> Diff {
    eq_value(a, b, policy, "")
}

impl fmt::Display for Diff {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Diff::Equal => write!(f, "equal"),
            Diff::FloatWithinTolerance { left, right, ulp } => {
                write!(f, "float-tolerance({left} vs {right}, {ulp} ulp)")
            }
            Diff::NotEqual { path, left, right } => {
                write!(f, "DIFF at '{path}': {left:?} vs {right:?}")
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn skalary() {
        let p = FloatPolicy::default();
        assert_eq!(deep_eq(&Value::Int(5), &Value::Int(5), &p), Diff::Equal);
        assert_eq!(
            deep_eq(&Value::Str("a".into()), &Value::Str("a".into()), &p),
            Diff::Equal
        );
        assert!(matches!(
            deep_eq(&Value::Int(5), &Value::Int(6), &p),
            Diff::NotEqual { .. }
        ));
    }

    #[test]
    fn floaty() {
        let p = FloatPolicy::default();
        // 0.1+0.2 != 0.3 bitowo — scisla polityka to zlapie
        assert!(matches!(
            deep_eq(&Value::Float(0.1 + 0.2), &Value::Float(0.3), &p),
            Diff::NotEqual { .. }
        ));
        let toler = FloatPolicy {
            rel_tol: 1e-9,
            max_ulp: 2,
            ..Default::default()
        };
        assert!(matches!(
            deep_eq(&Value::Float(0.1 + 0.2), &Value::Float(0.3), &toler),
            Diff::FloatWithinTolerance { .. }
        ));
        assert_eq!(
            deep_eq(&Value::Float(f64::NAN), &Value::Float(f64::NAN), &p),
            Diff::Equal
        );
        assert!(matches!(
            deep_eq(&Value::Float(f64::NAN), &Value::Float(1.0), &p),
            Diff::NotEqual { .. }
        ));
        assert_eq!(
            deep_eq(&Value::Float(-0.0), &Value::Float(0.0), &p),
            Diff::Equal
        );
        let zero_strict = FloatPolicy {
            signed_zero_equal: false,
            ..Default::default()
        };
        assert!(matches!(
            deep_eq(&Value::Float(-0.0), &Value::Float(0.0), &zero_strict),
            Diff::NotEqual { .. }
        ));
    }

    #[test]
    fn zagniezdzone_i_sciezka() {
        let p = FloatPolicy::default();
        let a = Value::List(vec![
            Value::Int(1),
            Value::Dict(vec![(Value::Str("k".into()), Value::Int(42))]),
        ]);
        let mut b = a.clone();
        if let Value::List(items) = &mut b {
            if let Value::Dict(pairs) = &mut items[1] {
                pairs[0].1 = Value::Int(43);
            }
        }
        match deep_eq(&a, &b, &p) {
            Diff::NotEqual { path, .. } => assert_eq!(path, "[1].k"),
            other => panic!("oczekiwano NotEqual, dostalem {:?}", other),
        }
        assert_eq!(deep_eq(&a, &a, &p), Diff::Equal);
    }
}
