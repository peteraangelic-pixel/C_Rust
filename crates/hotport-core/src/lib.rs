//! Model manifestu — wspólny język między profilerem, translatorem
//! a silnikiem weryfikacji (PLAN.md §3, komponenty [1]→[5]).
//! Std-only w fazie 0 (ADR-0004); serializacja serde dojdzie w CI.

use std::collections::BTreeMap;
use std::fmt;

/// Kształt typu obserwowany na wywołaniach (z tracera) lub zgłoszony ręcznie.
#[derive(Debug, Clone, PartialEq)]
pub enum TypeShape {
    Bool,
    Int {
        bits: u8,
        checked_overflow: bool,
    }, // K3: bignum vs i64/i128
    Float {
        policy_id: Option<String>,
    }, // K2: polityka tolerancji
    Str,
    Bytes,
    None,
    List(Box<TypeShape>),
    Tuple(Vec<TypeShape>),
    Dict {
        key: Box<TypeShape>,
        value: Box<TypeShape>,
        order_sensitive: bool,
    }, // K8
    Optional(Box<TypeShape>),
    Union(Vec<TypeShape>),
    Unknown, // brak obserwacji → poza kontraktem (Z5)
}

/// Aspekty kontraktu równoważności weryfikowane dla funkcji (PLAN.md §4.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ContractKind {
    ReturnType,     // K1
    ValueDeepEq,    // K2 (+FloatPolicy)
    IntOverflow,    // K3
    ArgMutation,    // K4
    Exceptions,     // K5
    EdgeSeeds,      // K6
    Determinism,    // K7
    IterationOrder, // K8
}

/// Jedna funkcja w manifeście profilowania.
#[derive(Debug, Clone)]
pub struct FunctionSpec {
    pub module: String,
    pub name: String,
    /// Sygnatura: nazwa argumentu → obserwowany kształt typu.
    pub args: BTreeMap<String, TypeShape>,
    pub ret: TypeShape,
    /// Liczba zaobserwowanych wywołań (czynnik "hot").
    pub calls: u64,
    /// Samoczas łącznie [ms] wg profilera.
    pub self_ms: f64,
    /// Czy funkcja mutuje argumenty (wg snapshotów tracera).
    pub mutates_args: bool,
    /// Czy rzuca/łapie wyjątki (obserwowane).
    pub raises: Vec<String>,
}

impl FunctionSpec {
    /// Prosty priorytet "hot path": czas własny × częstość.
    pub fn hotness(&self) -> f64 {
        self.self_ms * self.calls.max(1) as f64
    }
}

/// Status funkcji względem bramki (PLAN.md §4.3).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateStatus {
    /// Zweryfikowana równoważność + próg wydajności → promuj.
    Promoted,
    /// Różnica/brak dowodu → zostaje w Pythonie, czeka na człowieka (Z5).
    NeedsHuman,
    /// Poza zakresem tłumaczenia (IO, dynamiczne typy, mutacje w MVP...).
    OutOfScope,
}

#[derive(Debug, Clone)]
pub struct GateResult {
    pub function: String,
    pub status: GateStatus,
    pub l1_pass: Option<bool>,
    pub l2_pass: Option<bool>,
    pub l3_pass: Option<bool>,
    pub speedup: Option<f64>,
    pub notes: Vec<String>,
}

impl fmt::Display for GateStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            GateStatus::Promoted => "PROMOTED",
            GateStatus::NeedsHuman => "NEEDS-HUMAN",
            GateStatus::OutOfScope => "OUT-OF-SCOPE",
        };
        write!(f, "{s}")
    }
}

/// Skala werdyktu wydajnościowego (PLAN.md §4.3, adoptowane z review) —
/// promocja ≠ pochwała: poprawna migracja ×1.4 nie jest „performance win".
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpeedupVerdict {
    /// <1.2× — nie opłaca się wprowadzać.
    NotWorth,
    /// 1.2–2× — poprawne, ale nie promujemy jako „performance win".
    LowValue,
    /// 2–3×.
    Good,
    /// >3×.
    Excellent,
    /// >10× — materiał na showcase.
    Showcase,
}

pub fn classify_speedup(s: f64) -> SpeedupVerdict {
    if s >= 10.0 {
        SpeedupVerdict::Showcase
    } else if s >= 3.0 {
        SpeedupVerdict::Excellent
    } else if s >= 2.0 {
        SpeedupVerdict::Good
    } else if s >= 1.2 {
        SpeedupVerdict::LowValue
    } else {
        SpeedupVerdict::NotWorth
    }
}

impl fmt::Display for SpeedupVerdict {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            SpeedupVerdict::NotWorth => "NOT-WORTH",
            SpeedupVerdict::LowValue => "LOW-VALUE",
            SpeedupVerdict::Good => "GOOD",
            SpeedupVerdict::Excellent => "EXCELLENT",
            SpeedupVerdict::Showcase => "SHOWCASE",
        };
        write!(f, "{s}")
    }
}

/// Reguła bramki: promocja wymaga L1+L2 zielonych i progu speedup (§4.3).
pub fn gate(res: &GateResult, min_speedup: f64) -> GateStatus {
    let verified = matches!(res.l1_pass, Some(true)) && matches!(res.l2_pass, Some(true));
    let fast_enough = matches!(res.speedup, Some(s) if s >= min_speedup);
    if verified && fast_enough {
        GateStatus::Promoted
    } else {
        GateStatus::NeedsHuman
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec(calls: u64, ms: f64) -> FunctionSpec {
        let mut args = BTreeMap::new();
        args.insert("value".to_string(), TypeShape::Str);
        FunctionSpec {
            module: "validators".into(),
            name: "slug".into(),
            args,
            ret: TypeShape::Bool,
            calls,
            self_ms: ms,
            mutates_args: false,
            raises: vec![],
        }
    }

    #[test]
    fn hotness_rosnie_z_czestoscia() {
        let a = spec(10, 1.0);
        let b = spec(20, 1.0);
        assert!(b.hotness() > a.hotness());
    }

    #[test]
    fn skala_werdyktu_speedup() {
        use SpeedupVerdict::*;
        // nasze prawdziwe liczby z pierwszego zielonego CI (82400c3):
        assert_eq!(classify_speedup(4.52), Excellent); // uuid
        assert_eq!(classify_speedup(6.77), Excellent); // slug
        assert_eq!(classify_speedup(8.46), Excellent); // ipv4
                                                       // granice skali [REVIEW]:
        assert_eq!(classify_speedup(1.07), NotWorth);
        assert_eq!(classify_speedup(1.19), NotWorth);
        assert_eq!(classify_speedup(1.20), LowValue);
        assert_eq!(classify_speedup(1.99), LowValue);
        assert_eq!(classify_speedup(2.00), Good);
        assert_eq!(classify_speedup(2.99), Good);
        assert_eq!(classify_speedup(3.00), Excellent);
        assert_eq!(classify_speedup(10.0), Showcase);
    }

    #[test]
    fn bramka_wymaga_dowodu_i_szybkosci() {
        let ok = GateResult {
            function: "slug".into(),
            status: GateStatus::NeedsHuman,
            l1_pass: Some(true),
            l2_pass: Some(true),
            l3_pass: None,
            speedup: Some(2.0),
            notes: vec![],
        };
        assert_eq!(gate(&ok, 1.5), GateStatus::Promoted);
        let bez_dowodu = GateResult {
            l2_pass: Some(false),
            ..ok.clone()
        };
        assert_eq!(gate(&bez_dowodu, 1.5), GateStatus::NeedsHuman);
        let za_wolny = GateResult {
            speedup: Some(1.2),
            ..ok
        };
        assert_eq!(gate(&za_wolny, 1.5), GateStatus::NeedsHuman);
    }
}
