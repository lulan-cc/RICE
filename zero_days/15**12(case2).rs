//case2 - affected versions: 1.95
struct Bug<const N: usize> {
    A: [(); {
        let x = [(); Self::W];
        ()
    }],
}

fn main() {}