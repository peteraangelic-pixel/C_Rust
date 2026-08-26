//! CLI hotport — szkielet orkiestracji pipeline (faza 1 dołoży implementacje;
//! parsowanie argumentów std-only do czasu CI, gdzie wejdzie clap — ADR-0004).

use std::process::ExitCode;

#[derive(Debug, PartialEq)]
pub enum Command {
    Profile { target: String },
    Translate { manifest: String },
    Verify { manifest: String, gate: bool },
    Bench { manifest: String },
    Report { out: String },
    Help,
}

pub fn parse_args(args: &[String]) -> Result<Command, String> {
    match args.first().map(|s| s.as_str()) {
        Some("profile") => args
            .get(1)
            .map(|t| Command::Profile { target: t.clone() })
            .ok_or("profile: podaj cel (moduł/ścieżkę)".into()),
        Some("translate") => args
            .get(1)
            .map(|m| Command::Translate {
                manifest: m.clone(),
            })
            .ok_or("translate: podaj manifest".into()),
        Some("verify") => Ok(Command::Verify {
            manifest: args.get(1).cloned().unwrap_or_default(),
            gate: args.contains(&"--gate".to_string()),
        }),
        Some("bench") => args
            .get(1)
            .map(|m| Command::Bench {
                manifest: m.clone(),
            })
            .ok_or("bench: podaj manifest".into()),
        Some("report") => args
            .get(1)
            .map(|o| Command::Report { out: o.clone() })
            .ok_or("report: podaj plik wyjściowy".into()),
        Some("help") | None => Ok(Command::Help),
        Some(unknown) => Err(format!("nieznana komenda: {unknown}")),
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match parse_args(&args) {
        Ok(cmd) => {
            println!("hotport 0.0.1 (szkielet — PLAN.md faza 1)");
            match cmd {
                Command::Profile { target } => {
                    println!("profile: cel={target} —(TODO faza 1) tracer + manifest.json");
                }
                Command::Translate { manifest } => {
                    println!(
                        "translate: manifest={manifest} —(TODO faza 2) rdzeń deterministyczny"
                    );
                }
                Command::Verify { manifest, gate } => {
                    println!(
                        "verify: manifest={manifest} gate={gate} —(TODO faza 1) L1/L2 + exit-code"
                    );
                }
                Command::Bench { manifest } => {
                    println!("bench: manifest={manifest} —(TODO faza 3) criterion-style przed/po");
                }
                Command::Report { out } => {
                    println!("report: out={out} —(TODO faza 3) markdown + JSON");
                }
                Command::Help => {
                    println!("użycie: hotport <profile|translate|verify|bench|report> [argumenty]");
                }
            }
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("błąd: {e}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn parsowanie_komend() {
        assert_eq!(
            parse_args(&args(&["profile", "validators"])).unwrap(),
            Command::Profile {
                target: "validators".into()
            }
        );
        assert_eq!(
            parse_args(&args(&["verify", "m.json", "--gate"])).unwrap(),
            Command::Verify {
                manifest: "m.json".into(),
                gate: true
            }
        );
        assert!(parse_args(&args(&["profile"])).is_err());
        assert!(parse_args(&args(&["nieznane"])).is_err());
    }
}
