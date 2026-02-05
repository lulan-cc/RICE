//case1 - affected versions: 1.87-1.95
#![feature(adt_const_params, generic_const_parameter_types)]
#![expect(incomplete_features)]
#[derive(PartialEq)]
struct Inner<const N: usize>([u8; N]);
struct Outer<const N: usize, const M: Inner<N>>(Inner<N>);

fn main() {}