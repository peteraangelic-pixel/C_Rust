//! Spike fazy 0 (PLAN.md §Faza 0): ręczny port 3 funkcji biblioteki `validators`
//! (0.35.0) na czysty Rust, bez zależności zewnętrznych.
//!
//! Cel: udowodnić (a nie założyć), że semantyka da się przenieść i zweryfikować.
//! Wszystkie zasady wyprobowano EMPIRYCZNIE wobec Pythona 3.11 (patrz REPORT.md,
//! sekcja "złote reguły") — to złota tabela prawdy dla tego portu.
//!
//! Umowa (contract) rdzeni:
//! * `bool`  — wynik predykatu (valid/invalid),
//! * `None`  — wejście poza kontraktem ASCII → wywołujący MUSI skierować
//!             wywołanie do oryginalnej implementacji Pythona (Z5: deny, nie zgaduj).

pub mod cluster;
pub mod ffi;

/// Czy `s` jest poprawnym slugiem? Odpowiednik `re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", s)`
/// z validators 0.35.0 (pusty string → False, bo `if value else False`).
///
/// PUŁAPKA `$` w Pythonie: dopasowuje też PRZED JEDNYM końcowym '\n' —
/// empirycznie `slug("abc\n")` zwraca True, `slug("abc\n\n")` False.
/// Więc: obetnij maksymalnie jeden końcowy '\n' i sprawdź resztę.
pub fn slug_core(s: &str) -> bool {
    let body = if s.ends_with('\n') {
        &s[..s.len() - 1]
    } else {
        s
    };
    if body.is_empty() {
        return false; // python: falsy -> False (albo samo '\n' bez ciała)
    }
    let mut seen_hyphen = true; // start = jak po łączniku: wiodący '-' zabroniony (^[a-z0-9]+)
    for &b in body.as_bytes() {
        let alnum = b.is_ascii_lowercase() || b.is_ascii_digit();
        if alnum {
            seen_hyphen = false;
        } else if b == b'-' && !seen_hyphen {
            seen_hyphen = true;
        } else {
            return false; // podwójny '-', '-' na brzegu, wielka litera, nie-ASCII, kropka...
        }
    }
    !seen_hyphen // nie może kończyć się '-'
}

/// Odpowiednik `uuid.UUID(value)` (Python 3.11) dla stringów, w wersji
/// "bug-for-bug w obrębie ASCII" — złote reguły z probe'ów:
///
/// 1. `replace("urn:", "").replace("uuid:", "")` — MAŁE litery, DOWOLNE miejsce,
///    w tej kolejności (`uuid:` bez `urn:` też działa),
/// 2. `strip("{}")` — dowolna liczka `{`/`}` na końcach,
/// 3. usuń WSZYSTKIE `-`,
/// 4. długość == 32,
/// 5. `int(x, 16)`: znak '-' nigdy do niego nie dociera (krok 3 usuwa WSZYSTKIE
///    myślniki — więc '-' + kanoniczny z myślnikami jest VALID!), ale wiodący
///    `+` zostaje i int() go akceptuje (np. `+2bc1...` = '+' + 31 hex → VALID),
///    a pojedyncze `_` między cyframi również (PEP 515).
///
/// Wejścia nie-ASCII (Python przez `int()` akceptuje też cyfry Unicode Nd, np.
/// arabskie) zwracają `None` → routing do Pythona (świadoma decyzja, ADR-0005,
/// bo tablice Nd nie są dostępne w std).
pub fn uuid_core(s: &str) -> Option<bool> {
    if !s.is_ascii() {
        return None; // poza kontraktem ASCII (unicode Nd w int() — patrz ADR-0005)
    }
    let owned = s.replace("urn:", "").replace("uuid:", "");
    // strip "{" i "}" z obu końców (dowolna liczba)
    let t: String = owned
        .trim_matches(|c| c == '{' || c == '}')
        .replace('-', "");
    // krok 4: dokładnie 32 znaki (licząc `+`, `_` i białe znaki!)
    if t.len() != 32 {
        return Some(false);
    }
    // krok 5: int(x,16) najpierw OBCINA białe znaki na końcach — empirycznie
    // zbiór to spacja, \t, \n, \r, \x0b, \x0c (SZERSZY niż is_ascii_whitespace!,
    // które pomija \x0b). Uwaga: unicode-ws (\x85, \xa0) też działa w Pythonie,
    // ale łapie je wcześniej straż kontraktu ASCII (None → routing).
    let g = t.trim_matches(|c: char| matches!(c, ' ' | '\t' | '\n' | '\r' | '\x0b' | '\x0c'));
    let b = g.as_bytes();
    let mut i = 0;
    if !b.is_empty() && b[0] == b'+' {
        i = 1;
    }
    #[derive(PartialEq, Clone, Copy)]
    enum Last {
        Start,
        Digit,
        Underscore,
    }
    let mut last = Last::Start;
    let mut any_digit = false;
    while i < b.len() {
        let c = b[i];
        if c.is_ascii_hexdigit() {
            any_digit = true;
            last = Last::Digit;
        } else if c == b'_' {
            // PEP 515: pojedynczo i wyłącznie MIĘDZY cyframi hex
            if last != Last::Digit {
                return Some(false);
            }
            last = Last::Underscore;
        } else {
            return Some(false);
        }
        i += 1;
    }
    Some(any_digit && last == Last::Digit)
}

/// Parsuje oktet adresu IPv4 wg `_parse_octet` z ipaddress (3.11):
/// tylko cyfry ASCII, bez wiodących zer (poza samym "0"), wartość 0–255.
fn parse_octet(s: &str) -> Option<u32> {
    if s.is_empty() || !s.bytes().all(|b| b.is_ascii_digit()) {
        return None; // isdigit()+isascii() w ipaddress — cyfry unicode odpadają
    }
    if s.len() > 1 && s.starts_with('0') {
        return None; // leading zeros odrzucane od 3.9.5
    }
    let v: u32 = s.parse().ok()?;
    if v > 255 {
        return None;
    }
    Some(v)
}

/// Zamienia "a.b.c.d" na u32 (big-endian). Brak kompresji/heksów — string only.
fn parse_dotted(s: &str) -> Option<u32> {
    let parts: Vec<&str> = s.split('.').collect();
    if parts.len() != 4 {
        return None;
    }
    let mut v: u32 = 0;
    for p in parts {
        let o = parse_octet(p)?;
        v = (v << 8) | o;
    }
    Some(v)
}

/// Netmaska: prefix "0..32" (cyfry ASCII, wiodące zera DOZWOLONE — asymetria
/// względem oktetów!) albo maska kropkowana (prawidłowa, ciągła).
fn parse_netmask(s: &str) -> Option<u8> {
    if s.contains('.') {
        let m = parse_dotted(s)?;
        // ciągła maska: istnieje p, że m == !(0xFFFFFFFF >> p) ... sprawdźmy wszystkie p
        for p in 0u8..=32 {
            let mask: u32 = if p == 0 {
                0
            } else {
                (!0u32) << (32 - p as u32)
            };
            if m == mask {
                return Some(p);
            }
        }
        None // np. 255.0.255.0 — nieciągła
    } else {
        if s.is_empty() || !s.bytes().all(|b| b.is_ascii_digit()) {
            return None; // "+24", " 24", "_", unicode → NetmaskValueError
        }
        let p: u8 = s.parse().ok()?;
        if p > 32 {
            return None;
        }
        Some(p)
    }
}

/// Odpowiednik `validators.ipv4` (0.35.0) dla `private=None` (domyślne).
/// `cidr`/`strict`/`host_bit` jak w bibliotece; `strict` w validators wymusza
/// obecność dokładnie jednego '/', a `!host_bit` → `IPv4Network(strict=True)`.
pub fn ipv4_core(s: &str, cidr: bool, strict: bool, host_bit: bool) -> Option<bool> {
    if !s.is_ascii() {
        return None;
    }
    if s.is_empty() {
        return Some(false); // python: `if not value: return False`
    }
    if !cidr {
        return Some(parse_dotted(s).is_some());
    }
    if strict && s.matches('/').count() != 1 {
        return Some(false); // ValueError("expected CIDR") → False
    }
    let (addr_s, plen) = match s.split_once('/') {
        None => (s, 32u8), // "a.b.c.d" → /32
        Some((a, m)) => match parse_netmask(m) {
            // UWAGA (bug złapany przez CI): NIE używać `?` — parse_netmask→None
            // znaczy "błędna maska" → invalid (Some(false)), a nie "poza kontraktem"!
            Some(p) => (a, p),
            None => return Some(false), // NetmaskValueError → False
        },
    };
    // j/w: błąd adresu → invalid, NIE routing (bez `?`)
    let addr = match parse_dotted(addr_s) {
        Some(v) => v,
        None => return Some(false), // AddressValueError → False
    };
    let host_mask: u32 = if plen == 0 {
        !0u32
    } else {
        (1u32 << (32 - plen as u32)) - 1
    };
    if !host_bit && (addr & host_mask) != 0 {
        return Some(false); // IPv4Network(strict=True): bity hosta muszą być zerem
    }
    Some(true)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slug_l1() {
        for ok in [
            "123-asd-7sda",
            "123-k-123",
            "dac-12sa-459",
            "dac-12sa7-ad31as",
            "a",
        ] {
            assert!(slug_core(ok), "powinno byc valid: {ok}");
        }
        for bad in [
            "some.slug&",
            "1231321%",
            "   21312",
            "-47q-p--123",
            "",
            "A-b",
            "a--b",
            "abc-",
            "ń-abc",
        ] {
            assert!(!slug_core(bad), "powinno byc invalid: {bad}");
        }
        // pulapka koncowego '\n' (semantyka '$' w re)
        assert!(slug_core("abc\n"));
        assert!(!slug_core("abc\n\n"));
        assert!(!slug_core("abc\r"));
        assert!(!slug_core("\n"));
    }

    #[test]
    fn uuid_zlote_reguly() {
        assert_eq!(
            uuid_core("2bc1c94f-0deb-43e9-92a1-4775189ec9f8"),
            Some(true)
        );
        assert_eq!(
            uuid_core("2BC1C94F-0DEB-43E9-92A1-4775189EC9F8"),
            Some(true)
        );
        assert_eq!(uuid_core("2bc1c94f0deb43e992a14775189ec9f8"), Some(true));
        assert_eq!(
            uuid_core("{2bc1c94f-0deb-43e9-92a1-4775189ec9f8}"),
            Some(true)
        );
        assert_eq!(
            uuid_core("urn:uuid:2bc1c94f-0deb-43e9-92a1-4775189ec9f8"),
            Some(true)
        );
        assert_eq!(
            uuid_core("uuid:2bc1c94f-0deb-43e9-92a1-4775189ec9f8"),
            Some(true)
        );
        assert_eq!(
            uuid_core("{urn:uuid:2bc1c94f-0deb-43e9-92a1-4775189ec9f8}"),
            Some(true)
        );
        // pulapki int(): '+' i '_' (PEP 515) sa VALID, '-' nie
        assert_eq!(uuid_core("+2bc1c94f0deb43e992a14775189ec9f"), Some(true));
        assert_eq!(uuid_core("2bc1c94f_0deb43e992a14775189ec9f"), Some(true));
        assert_eq!(uuid_core("2bc1c94f0deb43e992a14775189ec9_f"), Some(true));
        // białe znaki obcinane przez int(): 30 hex + 2 ws = VALID (empiryczne!)
        assert_eq!(uuid_core("2bc1c94f0deb43e992a14775189ec9  "), Some(true));
        assert_eq!(uuid_core("\t2bc1c94f0deb43e992a14775189ec9 "), Some(true));
        assert_eq!(uuid_core("\x0b2bc1c94f0deb43e992a14775189ec9f"), Some(true)); // \x0b też
        assert_eq!(uuid_core("+\x0b2bc1c94f0deb43e992a14775189ec"), Some(false)); // tylko końce
        assert_eq!(uuid_core(" +2bc1c94f0deb43e992a14775189ec9"), Some(true));
        assert_eq!(uuid_core("+ 2bc1c94f0deb43e992a14775189ec9"), Some(false)); // ws w środku
        assert_eq!(uuid_core("2bc1 94f0deb43e992a14775189ec9f"), Some(false)); // ws w środku
        assert_eq!(uuid_core("-2bc1c94f0deb43e992a14775189ec9f"), Some(false));
        // wielkie URN: replace jest case-sensitive
        assert_eq!(
            uuid_core("URN:UUID:2bc1c94f-0deb-43e9-92a1-4775189ec9f8"),
            Some(false)
        );
        assert_eq!(uuid_core(" 2bc1c94f0deb43e992a14775189ec9f8"), Some(false));
        assert_eq!(uuid_core("2bc1c94f0deb43e992a14775189ec9f8x"), Some(false));
        assert_eq!(
            uuid_core("2bc1c94f-0deb-43e9-92a1-4775189ec9f"),
            Some(false)
        );
        assert_eq!(uuid_core(""), Some(false));
        // unicode (Nd) — poza kontraktem ASCII → routing do Pythona
        assert_eq!(uuid_core("٢bc1c94f0deb43e992a14775189ec9f8"), None);
    }

    #[test]
    fn ipv4_zlote_reguly() {
        // domyślne: cidr=true, strict=false, host_bit=true (sieć strict=False)
        let d = |s: &str| ipv4_core(s, true, false, true);
        assert_eq!(d("127.0.0.1"), Some(true));
        assert_eq!(d("0.0.0.0"), Some(true));
        assert_eq!(d("1.1.1.1/24"), Some(true));
        assert_eq!(d("1.1.1.1/0"), Some(true));
        assert_eq!(d("1.1.1.1/255.255.255.0"), Some(true));
        assert_eq!(d("1.1.1.1/0.0.0.0"), Some(true));
        assert_eq!(d("1.1.1.1/024"), Some(true)); // wiodące zero w PREFIKSIE jest ok
        assert_eq!(d("1.1.1.1/00"), Some(true)); // "00" → int=0 — też OK! (pierwszy przebieg CI
                                                 // złapał tu błędne oczekiwanie Some(false): w probe'u strict=True zawiniły bity
                                                 // hosta, nie maska — lekcja: oczekiwanie testu wyprowadzaj z probe'u o DOKŁADNIE
                                                 // tych parametrach, których używa testowany kod)
        assert_eq!(d("0127.0.0.1"), Some(false)); // ...a w oktecie adresu nie
        assert_eq!(d("1.1.1.01"), Some(false));
        assert_eq!(d("900.200.100.75"), Some(false));
        assert_eq!(d("abc.0.0.1"), Some(false));
        assert_eq!(d(" 1.1.1.1"), Some(false));
        assert_eq!(d("1.1.1.1/24 "), Some(false));
        assert_eq!(d("1.1.1.1/ 24"), Some(false));
        assert_eq!(d("1.1.1.1/+24"), Some(false));
        assert_eq!(d("1.1.1.1/33"), Some(false));
        assert_eq!(d("1.1.1.1/-1"), Some(false));
        assert_eq!(d("1.1.1.1/255.0.255.0"), Some(false)); // nieciągła maska
        assert_eq!(d("1.1.1.1/8.8.8.8"), Some(false)); // to nie maska
        assert_eq!(d("1.1.1.1/2_4"), Some(false));
        assert_eq!(d("1.1.1.1/24/24"), Some(false));
        assert_eq!(d("01.1.1.1/8"), Some(false));
        // strict (validators): wymaga dokładnie jednego '/'
        assert_eq!(ipv4_core("1.1.1.1", true, true, true), Some(false));
        assert_eq!(ipv4_core("1.2.3.4/24", true, true, true), Some(true));
        // host_bit=False → IPv4Network strict=True: bity hosta zerem
        assert_eq!(ipv4_core("1.2.3.4/24", true, false, false), Some(false));
        assert_eq!(ipv4_core("12.12.12.0/24", true, false, false), Some(true));
        assert_eq!(ipv4_core("1.1.1.1", true, false, false), Some(true)); // /32
                                                                          // cidr=False → czysty adres
        assert_eq!(ipv4_core("1.2.3.4/24", false, false, true), Some(false));
        assert_eq!(ipv4_core("1.1.1.1", false, false, true), Some(true));
        assert_eq!(ipv4_core("", true, false, true), Some(false));
        assert_eq!(ipv4_core("1.1.1.1/24", false, false, true), Some(false));
    }
}
