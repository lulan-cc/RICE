//affected versions: 1.81-1.93
pub trait Super<X> {
    type X;
}

impl<T> Clone for Box<dyn Super<X = T>> {
    fn clone(&self) -> Self {
        unimplemented!();
    }
}

pub fn main() {}
