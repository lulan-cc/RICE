// affected versions: 1.94
#![feature(fn_delegation)]
extern "C" {
    fn a() {
        reuse foo {}
    }
}

pub fn main() {}