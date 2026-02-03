//affected versions: 1.78-1.95
trait Trait {
    type Assoc;
}

fn foo<F,T>(mut f: F) -> i32 
where F: FnMut(<T as Trait>::Assoc) -> i32 {
    (|x| f(x))(foo::<F, T>(f))
}

fn main() {}