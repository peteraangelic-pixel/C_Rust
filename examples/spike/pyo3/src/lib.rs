//! Binding PyO3 dla rdzenia spike'a. Budowane w CI (sandbox dev nie ma
//! dostępu do crates.io — ADR-0004). Woła TE SAME funkcje co ścieżka ctypes,
//! więc weryfikacja równoważności pokrywa oba transporty.

use pyo3::prelude::*;

/// Zwraca True/False albo None, gdy wejście jest poza kontraktem ASCII
/// (wtedy Python shim kieruje wywołanie do oryginału — Z5).
#[pyfunction]
fn slug_is_valid(value: &str) -> bool {
    hotport_spike_core::slug_core(value)
}

#[pyfunction]
fn uuid_is_valid(value: &str) -> Option<bool> {
    hotport_spike_core::uuid_core(value)
}

#[pyfunction]
fn ipv4_is_valid(value: &str, cidr: bool, strict: bool, host_bit: bool) -> Option<bool> {
    hotport_spike_core::ipv4_core(value, cidr, strict, host_bit)
}

#[pymodule]
fn hotport_spike(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(slug_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(uuid_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(ipv4_is_valid, m)?)?;
    Ok(())
}
