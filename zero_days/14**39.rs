//affected versions: 1.91-1.95
#![feature(coroutines, stmt_expr_attributes)]

const _: for<'a> fn() -> i32 = #[coroutine] || -> i32 { yield 0; return 1; };

fn main(){}