// affected versions: 1.86-1.93
#![feature(min_generic_const_args)]
#![allow(incomplete_features)]

trait Maybe<T> {}

trait MyTrait<const F: fn() -> ()> {}

fn foo<'a>(x: &'a ()) -> &'a () { x }

impl<T> Maybe<T> for T where T: MyTrait<{ foo }> {}

fn main() {}