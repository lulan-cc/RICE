//affected versions: 1.92
type Variant<'a, T> = SomeEnum<T>;

enum SomeEnum<T> {
    SomeVariant { t: T }
}

fn annot_reference_named_lifetime<'a>(_d: &'a u32) {
    let c = 66;
    Variant::SomeVariant::<&'a u32> { t: &c };
}

fn main() {}