//! Statystyki benchmarkowe i raport przed/po (Z7: raport = dowód wartości).
//! Std-only (ADR-0004).

use std::time::Duration;

/// Próbka czasu wykonania (jedna iteracja / batch).
#[derive(Debug, Clone, Copy)]
pub struct Sample {
    pub nanos: u128,
    pub ops: u64, // ile operacji obejmowała próbka
}

#[derive(Debug, Clone, PartialEq)]
pub struct Stats {
    pub n: u64,
    pub median_ns_per_op: f64,
    pub p05_ns_per_op: f64,
    pub p95_ns_per_op: f64,
    pub mean_ns_per_op: f64,
}

impl Stats {
    /// Zakłada niepustą listę próbek; sortuje kopię.
    pub fn from_samples(samples: &[Sample]) -> Option<Stats> {
        if samples.is_empty() {
            return None;
        }
        let mut per_op: Vec<f64> = samples
            .iter()
            .filter(|s| s.ops > 0)
            .map(|s| s.nanos as f64 / s.ops as f64)
            .collect();
        if per_op.is_empty() {
            return None;
        }
        per_op.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let n = per_op.len() as u64;
        let pick = |q: f64| -> f64 {
            let idx = ((q * (n - 1) as f64).round()) as usize;
            per_op[idx.min(per_op.len() - 1)]
        };
        Some(Stats {
            n,
            median_ns_per_op: pick(0.5),
            p05_ns_per_op: pick(0.05),
            p95_ns_per_op: pick(0.95),
            mean_ns_per_op: per_op.iter().sum::<f64>() / n as f64,
        })
    }
}

/// Wiersz raportu: jedna funkcja × implementacja.
#[derive(Debug, Clone)]
pub struct BenchRow {
    pub function: String,
    pub implementation: String, // "python" | "rust" | ...
    pub stats: Stats,
}

/// Prosty raport tekstowy; speedup liczymy median python/rust.
pub fn render_report(rows: &[BenchRow]) -> String {
    let mut out = String::from("# Benchmark przed/po (median ns/op)\n\n| funkcja | implementacja | median | p95 | x szybciej |\n|---|---|---|---|---|\n");
    let mut functions: Vec<String> = rows.iter().map(|r| r.function.clone()).collect();
    functions.sort();
    functions.dedup();
    for f in &functions {
        let mut py = None;
        let mut rs = None;
        for r in rows {
            if &r.function == f {
                match r.implementation.as_str() {
                    "python" => py = Some(&r.stats),
                    "rust" => rs = Some(&r.stats),
                    _ => {}
                }
            }
        }
        let mut speedup = String::new();
        if let (Some(p), Some(r)) = (py, rs) {
            if r.median_ns_per_op > 0.0 {
                speedup = format!("{:.2}x", p.median_ns_per_op / r.median_ns_per_op);
            }
        }
        for (name, st) in [("python", py), ("rust", rs)] {
            if let Some(s) = st {
                out.push_str(&format!(
                    "| {} | {} | {:.0} | {:.0} | {} |\n",
                    f,
                    name,
                    s.median_ns_per_op,
                    s.p95_ns_per_op,
                    if name == "python" { &speedup } else { "" }
                ));
            }
        }
    }
    out
}

/// Zmierz czas wykonania `f` w batchach (pomiar własny, bez zewn. crates).
pub fn measure<F: FnMut()>(ops_per_batch: u64, batches: u64, mut f: F) -> Vec<Sample> {
    let mut out = Vec::with_capacity(batches as usize);
    for _ in 0..batches {
        let t0 = std::time::Instant::now();
        for _ in 0..ops_per_batch {
            f();
        }
        let dt = t0.elapsed();
        out.push(Sample { nanos: dt.as_nanos(), ops: ops_per_batch });
    }
    out
}

impl From<Sample> for Duration {
    fn from(s: Sample) -> Duration {
        Duration::from_nanos(s.nanos as u64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn statystyki_percentyle() {
        let samples: Vec<Sample> = [10u128, 20, 30, 40, 50]
            .iter()
            .map(|&n| Sample { nanos: n, ops: 1 })
            .collect();
        let s = Stats::from_samples(&samples).unwrap();
        assert_eq!(s.n, 5);
        assert_eq!(s.median_ns_per_op, 30.0);
        assert_eq!(s.p05_ns_per_op, 10.0);
        assert_eq!(s.p95_ns_per_op, 50.0);
        assert_eq!(s.mean_ns_per_op, 30.0);
    }

    #[test]
    fn pusta_lista_to_none() {
        assert!(Stats::from_samples(&[]).is_none());
    }

    #[test]
    fn raport_ma_speedup() {
        let rows = vec![
            BenchRow {
                function: "slug".into(),
                implementation: "python".into(),
                stats: Stats { n: 3, median_ns_per_op: 100.0, p05_ns_per_op: 90.0, p95_ns_per_op: 110.0, mean_ns_per_op: 100.0 },
            },
            BenchRow {
                function: "slug".into(),
                implementation: "rust".into(),
                stats: Stats { n: 3, median_ns_per_op: 25.0, p05_ns_per_op: 20.0, p95_ns_per_op: 30.0, mean_ns_per_op: 25.0 },
            },
        ];
        let r = render_report(&rows);
        assert!(r.contains("4.00x"));
        assert!(r.contains("| slug | python |"));
    }
}
