//! Binding PyO3 dla rdzenia spike'a (budowane w CI — ADR-0004).
//! Woła TE SAME funkcje co ścieżka ctypes; różnica to tylko koszt przejścia.

use pyo3::prelude::*;
use rayon::prelude::*;

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

/// BATCH API [rayon]: jedno przejście FFI na CAŁĄ listę + wszystkie rdzenie.
///
/// Kontrakt batcha (odmiana ADR-0005): elementy poza kontraktem ASCII dają
/// false (batch = szybka ścieżka; per-item routing nie ma sensu masowo).
/// `py.allow_threads` ZWALNIA GIL: pythonowe wątki żyją, rayon kręci się
/// na wszystkich rdzeniach (work-stealing).
#[pyfunction]
fn ipv4_batch(py: Python<'_>, items: Vec<String>) -> Vec<bool> {
    py.allow_threads(move || {
        items
            .into_par_iter()
            .map(|s| hotport_spike_core::ipv4_core(&s, true, false, true).unwrap_or(false))
            .collect()
    })
}

#[pymodule]
fn hotport_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(slug_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(uuid_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(ipv4_is_valid, m)?)?;
    m.add_function(wrap_pyfunction!(ipv4_batch, m)?)?;
    Ok(())
}
