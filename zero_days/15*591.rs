// affected versions: 1.87-1.95
#![feature(adt_const_params)]
#![feature(unsized_const_params)]

#[derive(Clone)]
struct S<const L: [u8]>;

const A: [u8];

impl<const N: i32> Copy for S<A> {}
impl<const M: usize> Copy for S<A> {}

fn main() {}