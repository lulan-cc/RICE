// affected versions: 1.89-1.95
#![feature(sized_hierarchy)]
#![feature(non_lifetime_binders)]

use std::marker::PointeeSized;

pub trait Foo<T: PointeeSized> {
    type Bar<K: PointeeSized>: PointeeSized;
}

pub fn f<T1, T2>(a: T1, b: T2)
where
    T1: for<K, T> Foo<usize, Bar<K> = T>,
    T2: for<K, T> Foo<usize, Bar<K> = <T1 as Foo<usize>>::Bar<T>>,
{
}