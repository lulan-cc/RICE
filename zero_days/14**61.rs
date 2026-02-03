// affected versions: 1.48-1.92
trait Trait {
    type Assoc;
}

impl Trait for u8 {
    type Assoc = i8;
}

struct Struct<T: Trait> {
    member: T::Assoc,
}

unsafe extern "C" {
    static VAR: Struct<i8>;
}


fn main() {}