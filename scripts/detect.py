#!/usr/bin/env python3
"""
检测和保存触发 ICE (Internal Compiler Error) 的代码
功能：
1. 编译 ./code_gen 下的代码。
2. 自动清理编译生成的二进制文件（不占用磁盘）。
3. 如果发现 ICE，将源码和报错日志保存到 ./pending_review/ice。
4. 支持断点续传（通过日志记录跳过已检测文件）。
"""

import subprocess
import tempfile
from pathlib import Path
import shutil
import sys
import os
import time

# ================= 配置区域 =================
# 1. 编译器命令/路径
# 如果要测试系统安装的 nightly:
RUSTC_BIN = "rustc" 
RUSTC_ARGS = ["+nightly-x86_64-unknown-linux-gnu"]

# 如果要测试你自己编译的版本 (取消下面注释并修改路径):
# RUSTC_BIN = "/home/lulan/MyProjects/rustc-fuzz/rust/build/host/stage1/bin/rustc"
# RUSTC_ARGS = []

# 2. 路径配置
BASE_DIR = Path(__file__).resolve().parent
CODEGEN_DIR = (BASE_DIR / "code_gen").resolve()
ICE_DIR = (BASE_DIR / "pending_review" / "ice").resolve()
LOG_FILE = (BASE_DIR / "pending_review" / "checked_files.log").resolve()

# 3. 批次配置
# 每处理多少个文件刷新一次日志到磁盘
BATCH_SIZE = 50 
# 编译超时时间 (秒)
TIMEOUT_SEC = 10.0 
# ===========================================

def ensure_dirs():
    ICE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_checked_files() -> set[str]:
    """加载已处理的文件列表，支持断点续传"""
    if not LOG_FILE.exists():
        return set()
    try:
        # 读取时忽略空行
        return {
            line.strip()
            for line in LOG_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    except Exception as e:
        print(f"[Warn] 读取日志文件失败: {e}")
        return set()

def check_ice(rs_file: Path) -> tuple[bool, str]:
    """
    编译单个文件并检测是否 ICE。
    使用 TemporaryDirectory 确保编译产物（二进制文件）在函数结束时自动删除。
    """
    try:
        # 创建临时目录用于存放编译产物
        with tempfile.TemporaryDirectory() as tmpdir:
            # 输出文件的路径（在临时目录里）
            out_bin = Path(tmpdir) / rs_file.stem
            
            cmd = [RUSTC_BIN] + RUSTC_ARGS + [
                str(rs_file),
                "-o", str(out_bin) # 指定输出位置到临时目录
            ]

            # 执行编译
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SEC,
                cwd=tmpdir # 在临时目录执行，避免污染源码目录
            )

            # 合并 stdout 和 stderr，因为 ICE 可能出现在任何一处
            output = (result.stderr or "") + (result.stdout or "")

            # ICE 特征匹配
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

def save_ice_report(rs_file: Path, error_log: str):
    """保存触发 ICE 的代码和日志"""
    try:
        # 保持相对目录结构
        rel_path = rs_file.relative_to(CODEGEN_DIR)
        target_dir = ICE_DIR / rel_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. 复制源代码
        shutil.copy2(rs_file, target_dir / rs_file.name)

        # 2. 写入报错日志
        log_path = target_dir / f"{rs_file.stem}.err.log"
        log_path.write_text(error_log, encoding="utf-8")
        
        return True
    except Exception as e:
        print(f"\n[Error] 保存 ICE 失败: {e}")
        return False

def main():
    if not CODEGEN_DIR.exists():
        print(f"[Error] 源代码目录不存在: {CODEGEN_DIR}")
        sys.exit(1)

    ensure_dirs()
    
    # 1. 加载历史记录
    checked_files = load_checked_files()
    print(f"历史已检测文件数: {len(checked_files)}")

    # 2. 扫描文件
    print("正在扫描 Rust 文件列表...")
    # rglog 返回的是生成器，转成 list 方便显示进度条
    # 如果文件有几百万个，建议去掉 list() 改为直接迭代
    all_files = list(CODEGEN_DIR.rglob("*.rs"))
    total_files = len(all_files)
    print(f"待扫描文件总数: {total_files}")

    processed_count = 0
    skipped_count = 0
    ice_found_count = 0

    # 3. 打开日志文件准备追加
    # buffering=1 表示行缓冲，但我们会在循环中手动 flush 以保万全
    with open(LOG_FILE, "a", encoding="utf-8", buffering=1) as log_f:
        
        start_time = time.time()
        
        for idx, rs_file in enumerate(all_files, 1):
            rel_path_str = str(rs_file.relative_to(CODEGEN_DIR))

            # --- 跳过已检测 ---
            if rel_path_str in checked_files:
                skipped_count += 1
                continue

            # --- 显示进度 (覆盖当前行) ---
            # 简单的进度显示，避免刷屏
            print(f"\r[{idx}/{total_files}] Checking: {rel_path_str[:50]:<50}", end="", flush=True)

            # --- 执行检测 ---
            is_ice, error_msg = check_ice(rs_file)

            # --- 处理 ICE ---
            if is_ice:
                # 另起一行打印发现信息
                print(f"\n[!!! ICE DETECTED !!!] {rel_path_str}")
                if save_ice_report(rs_file, error_msg):
                    ice_found_count += 1
            
            # --- 记录日志 ---
            # 无论成功失败，只要没崩，都算检测过了
            log_f.write(rel_path_str + "\n")
            processed_count += 1

            # --- 批次刷新 ---
            # 每 BATCH_SIZE 个文件强制刷入磁盘，防止脚本意外中断丢失进度
            if processed_count % BATCH_SIZE == 0:
                log_f.flush()

    # 结束
    duration = time.time() - start_time
    print("\n" + "="*40)
    print(f"检测完成，耗时: {duration:.1f} 秒")
    print(f"本次检测: {processed_count}")
    print(f"跳过历史: {skipped_count}")
    print(f"发现 ICE: {ice_found_count}")
    print(f"ICE 保存路径: {ICE_DIR}")
    print(f"进度记录文件: {LOG_FILE}")
    print("="*40)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Stop] 用户中断检测。进度已保存。")