// affected versions: 1.95
#![feature(repr_simd)]
#[repr(simd)]
struct Simd<T, const N: usize>([T; N]);

unsafe extern "C" {
    static VAR: Simd<u8, 0>;
}

fn main() {}