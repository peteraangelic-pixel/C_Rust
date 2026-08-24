/// WYGENEROWANE AUTOMATYCZNIE przez hotport_trans v0 — NIE EDYTOWAĆ
pub fn code_ok(code: &str, prefix: &str) -> Option<bool> {
    if ((code).chars().count()) != (10) {
        return Some(false);
    }
    return Some(((code).starts_with(prefix)) && (!((code).ends_with("-"))));
}
