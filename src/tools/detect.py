import subprocess
import tempfile
from pathlib import Path
import shutil
import sys
import time

# ================= 配置区域 =================
RUSTC_BIN = "rustc"
RUSTC_ARGS = ["+nightly-x86_64-unknown-linux-gnu"]
BATCH_SIZE = 50  # 批量刷新输出
TIMEOUT_SEC = 10.0  # 编译超时时间 (秒)
# ===========================================

def check_ice_dir(
    code_dir: str | Path,
    ice_output_dir: str | Path,
) -> dict[str, int]:
    """
    检测指定目录下的 Rust 文件是否触发 ICE。

    参数:
        code_dir: 待检测 Rust 文件目录
        ice_output_dir: ICE 触发源码和日志保存目录

    返回:
        dict: 检测统计信息，包括总文件数、ICE 发现数
    """

    code_dir = Path(code_dir).resolve()
    ice_dir = Path(ice_output_dir).resolve()
    ice_dir.mkdir(parents=True, exist_ok=True)

    if not code_dir.exists():
        print(f"[Error] 待检测目录不存在: {code_dir}")
        return {"total_files": 0, "ice_found": 0}

    def compile_and_check(rs_file: Path) -> tuple[bool, str]:
        """编译单个文件并检测 ICE"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out_bin = Path(tmpdir) / rs_file.stem
                cmd = [RUSTC_BIN] + RUSTC_ARGS + [
                    str(rs_file),
                    "-o", str(out_bin)
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SEC,
                    cwd=tmpdir
                )
                output = (result.stderr or "") + (result.stdout or "")
                is_ice = (
                    "internal compiler error" in output or
                    "thread 'rustc' panicked at" in output or
                    "Box<Any>" in output or
                    "delay_span_bug" in output or
                    "query stack during panic" in output
                )
                return is_ice, output
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except Exception as e:
            return False, f"Script Error: {e}"

    def save_ice(rs_file: Path, error_log: str) -> bool:
        """保存触发 ICE 的源码和日志"""
        try:
            rel_path = rs_file.relative_to(code_dir)
            target_dir = ice_dir / rel_path.parent
            target_dir.mkdir(parents=True, exist_ok=True)

            # 保存源码
            shutil.copy2(rs_file, target_dir / rs_file.name)

            # 保存错误日志
            log_path = target_dir / f"{rs_file.stem}.err.log"
            log_path.write_text(error_log, encoding="utf-8")
            return True
        except Exception as e:
            print(f"[Error] 保存 ICE 失败: {e}")
            return False

    all_files = list(code_dir.rglob("*.rs"))
    total_files = len(all_files)
    ice_found_count = 0
    processed_count = 0

    start_time = time.time()

    for idx, rs_file in enumerate(all_files, 1):
        print(f"\r[{idx}/{total_files}] Checking: {rs_file.relative_to(code_dir)}", end="", flush=True)
        is_ice, error_msg = compile_and_check(rs_file)

        if is_ice:
            print(f"\n[!!! ICE DETECTED !!!] {rs_file.relative_to(code_dir)}")
            if save_ice(rs_file, error_msg):
                ice_found_count += 1

        processed_count += 1
        if processed_count % BATCH_SIZE == 0:
            sys.stdout.flush()

    duration = time.time() - start_time
    print("\n" + "="*40)
    print(f"检测完成，耗时: {duration:.1f} 秒")
    print(f"检测文件数: {processed_count}")
    print(f"发现 ICE: {ice_found_count}")
    print(f"ICE 保存路径: {ice_dir}")
    print("="*40)

    return {"total_files": processed_count, "ice_found": ice_found_count}
