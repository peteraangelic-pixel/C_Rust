//! Warstwa FFI (C ABI) do wywołań z Pythona przez `ctypes`.
//!
//! Umowa: 1 = true, 0 = false, -1 = wejście poza kontraktem (routing do Pythona).
//! String przekazywany jako (ptr, len) UTF-8; niepoprawny UTF-8 → -1.
//!
//! UWAGA: to ścieżka "sandboxowa" (bez crates.io). W produkcyjnym przebiegu
//! używany jest binding PyO3 (examples/spike/pyo3) wywołujący TE SAME funkcje
//! rdzenia — FFI i PyO3 różnią się wyłącznie kosztem przejścia przez granicę.

use std::ffi::c_char;
use std::str::Utf8Error;

unsafe fn borrow<'a>(ptr: *const c_char, len: usize) -> Result<&'a str, Utf8Error> {
    if ptr.is_null() {
        return Err(Utf8Error {});
    }
    let bytes = std::slice::from_raw_parts(ptr as *const u8, len);
    std::str::from_utf8(bytes)
}

fn opt_to_i32(v: Option<bool>) -> i32 {
    match v {
        Some(true) => 1,
        Some(false) => 0,
        None => -1,
    }
}

/// # Safety
/// `ptr` musi wskazywać na `len` poprawnych bajtów przez czas wywołania.
#[no_mangle]
pub unsafe extern "C" fn hotport_slug_is_valid(ptr: *const c_char, len: usize) -> i32 {
    match borrow(ptr, len) {
        Ok(s) => opt_to_i32(Some(crate::slug_core(s))),
        Err(_) => -1,
    }
}

/// # Safety
/// `ptr` musi wskazywać na `len` poprawnych bajtów przez czas wywołania.
#[no_mangle]
pub unsafe extern "C" fn hotport_uuid_is_valid(ptr: *const c_char, len: usize) -> i32 {
    match borrow(ptr, len) {
        Ok(s) => opt_to_i32(crate::uuid_core(s)),
        Err(_) => -1,
    }
}

/// # Safety
/// `ptr` musi wskazywać na `len` poprawnych bajtów; flagi `cidr`/`strict`/`host_bit`
/// przyjmują wartości 0/1.
#[no_mangle]
pub unsafe extern "C" fn hotport_ipv4_is_valid(
    ptr: *const c_char,
    len: usize,
    cidr: u8,
    strict: u8,
    host_bit: u8,
) -> i32 {
    match borrow(ptr, len) {
        Ok(s) => opt_to_i32(crate::ipv4_core(s, cidr != 0, strict != 0, host_bit != 0)),
        Err(_) => -1,
    }
}
