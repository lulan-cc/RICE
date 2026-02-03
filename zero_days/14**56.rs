// affected versions: 1.83-1.93
#![feature(generic_const_exprs)]

trait MyTrait<T> {}

fn bug<'a>() -> impl MyTrait<[(); { |x: &'a u32| { x }; 4 }]> {
    todo!()
}

fn main() {}