//affected versions: 1.84-1.95
trait OpaqueTrait {}
type OpaqueType = &dyn OpaqueTrait;
impl<T: std::mem::TransmuteFrom<(), ()>> OpaqueTrait for T {}
impl<T> OpaqueTrait for &T where T: OpaqueTrait {}
pub fn main() {}