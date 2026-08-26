//! Deterministyczny rdzeń translacji — mapa typów Python→Rust i tabela
//! mapowań stdlib z PUŁAPKAMI (PLAN.md §3 [2b]). Std-only (ADR-0004).

use std::collections::BTreeMap;

/// Wynik mapowania typu: cel + czy mapowanie jest bezstratne.
#[derive(Debug, Clone, PartialEq)]
pub struct TypeMapping {
    pub rust_type: String,
    pub lossless: bool,
    pub note: Option<&'static str>,
}

/// Mapowanie typów dla kształtów obserwowanych w manifeście (hotport-core).
pub fn map_type(py: &str) -> TypeMapping {
    match py {
        "bool" => TypeMapping { rust_type: "bool".into(), lossless: true, note: None },
        "int" => TypeMapping {
            rust_type: "i64".into(),
            lossless: false,
            note: Some("Python int jest dowolnej precyzji (K3): i64 + sprawdzany overflow, w razie przekroczenia → routing do Pythona"),
        },
        "float" => TypeMapping { rust_type: "f64".into(), lossless: true, note: None },
        "str" => TypeMapping { rust_type: "String".into(), lossless: true, note: None },
        "bytes" => TypeMapping { rust_type: "Vec<u8>".into(), lossless: true, note: None },
        "None" => TypeMapping { rust_type: "()".into(), lossless: true, note: None },
        "list" => TypeMapping { rust_type: "Vec<T>".into(), lossless: true, note: None },
        "tuple" => TypeMapping { rust_type: "(T, ..)".into(), lossless: true, note: None },
        "dict" => TypeMapping {
            rust_type: "IndexMap<K, V>".into(),
            lossless: false,
            note: Some("Kolejność iteracji (K8): IndexMap; czysta HashMap ją gubi"),
        },
        other => TypeMapping {
            rust_type: format!("/* {other}: nieznane */"),
            lossless: false,
            note: Some("Typ nieobsługiwany w MVP — poza zakresem (Z5)"),
        },
    }
}

/// Jedno mapowanie API stdlib: pythonowe wywołanie → rustowy odpowiednik.
#[derive(Debug, Clone)]
pub struct ApiMapping {
    pub python: &'static str,
    pub rust: &'static str,
    pub pitfalls: &'static [&'static str],
}

/// Tabela mapowań stdlib v0 — każda pozycja z listą znanych pułapek.
pub fn stdlib_map() -> BTreeMap<&'static str, ApiMapping> {
    let mut m = BTreeMap::new();
    m.insert(
        "str.strip",
        ApiMapping {
            python: "s.strip() / s.strip(chars)",
            rust: "s.trim() / s.trim_matches(..)",
            pitfalls: &[
                "strip() bez argumentu tnie UNIKODOWE białe znaki — trim() tylko ASCII (użyj unicode-whitespace)",
                "strip(chars) to ZBIÓR znaków, nie prefiks/sufiks",
            ],
        },
    );
    m.insert(
        "str.split",
        ApiMapping {
            python: "s.split(sep) / s.split()",
            rust: "s.split(sep) / s.split_whitespace()",
            pitfalls: &[
                "split() bez argumentu łączy sekwencje białych znaków i goni wiodące — split_whitespace() to samo",
                "split('') to błąd w Pythonie, ale split(\"\") w Rust dzieli po bajtach",
            ],
        },
    );
    m.insert(
        "re.match",
        ApiMapping {
            python: "re.match(pattern, s)",
            rust: "regex::Regex (albo fancy-regex)",
            pitfalls: &[
                "regex crate: bez backreference/lookaround → fancy-regex",
                "Semantyka Unicode różna (klasy \\d, \\w dopasowują Nd/word w Pythonie)",
                "Flagi: re.IGNORECASE dotyczy Unicode case folding",
            ],
        },
    );
    m.insert(
        "int(s)",
        ApiMapping {
            python: "int(s) / int(s, 16)",
            rust: "s.parse::<i64>()",
            pitfalls: &[
                "int() obcina białe znaki ASCII, akceptuje znak '+', podkreślniki PEP 515 i cyfry Unicode Nd",
                "Dowolna precyzja (K3) — parse do i64/u64 z checked overflow",
            ],
        },
    );
    m.insert(
        "dict",
        ApiMapping {
            python: "dict / {}",
            rust: "IndexMap (kolejność!) / HashMap",
            pitfalls: &["Kolejność wstawiania jest częścią obserwowalnego zachowania (K8)"],
        },
    );
    m.insert(
        "json.dumps",
        ApiMapping {
            python: "json.dumps(obj)",
            rust: "serde_json::to_string",
            pitfalls: &[
                "Python: NaN/Infinity domyślnie legalne w output; serde_json — nie",
                "spacje po ':' i ',' różnią się od serde_json",
                "non-ASCII: Python domyślnie ensure_ascii=True (\\uXXXX)",
            ],
        },
    );
    m
}

/// Interfejs translatora: rdzeń deterministyczny + (później, ADR-0003)
/// opcjonalna warstwa LLM jako osobny backend — LLM nigdy nie omija weryfikacji.
pub trait Translator {
    /// Zwraca szkielet funkcji Rust dla podanej sygnatury (bez ciała — to robi backend).
    fn skeleton(&self, module: &str, function: &str, args: &[(&str, &str)], ret: &str) -> String;
}

/// Backend deterministyczny (jedyny w v1).
pub struct RuleTranslator;

impl Translator for RuleTranslator {
    fn skeleton(&self, module: &str, function: &str, args: &[(&str, &str)], ret: &str) -> String {
        let args_s = args
            .iter()
            .map(|(n, t)| format!("{}: {}", rust_arg_name(n), map_type(t).rust_type))
            .collect::<Vec<_>>()
            .join(", ");
        format!("/// port z {module}.{function}\npub fn {function}({args_s}) -> {ret} {{\n    todo!(\"uzupełnia reguły + weryfikacja bramką\")\n}}\n")
    }
}

fn rust_arg_name(name: &str) -> String {
    // 'value' ok; słowa zarezerwowane → sufiks
    if matches!(
        name,
        "type" | "ref" | "fn" | "match" | "box" | "move" | "loop"
    ) {
        format!("{name}_")
    } else {
        name.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mapa_typow_z_pulapkami() {
        assert!(map_type("int").lossless == false);
        assert!(map_type("int").note.is_some());
        assert_eq!(map_type("str").rust_type, "String");
        assert!(map_type("dict").note.unwrap().contains("K8"));
    }

    #[test]
    fn stdlib_map_ma_pulapki_re() {
        let m = stdlib_map();
        let re = m.get("re.match").expect("re.match w mapie");
        assert!(!re.pitfalls.is_empty());
    }

    #[test]
    fn szkielet_funkcji() {
        let t = RuleTranslator;
        let s = t.skeleton("validators", "slug", &[("value", "str")], "bool");
        assert!(s.contains("pub fn slug(value: String) -> bool"));
        assert!(s.contains("port z validators.slug"));
        // slowo zarezerwowane jako arg
        let s2 = t.skeleton("m", "f", &[("type", "str")], "bool");
        assert!(s2.contains("type_: String"));
    }
}
