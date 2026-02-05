import os
import subprocess
import tempfile
import sys
import glob
import shutil
import time

# ================= 配置区域 =================

# 1. rustc 编译器的绝对路径
#    请确保这是你构建的 stage1 编译器 (带 instrument-coverage)
RUSTC_BIN = "/home/lulan/MyProjects/rustc-fuzz/rust/build/host/stage1/bin/rustc"

# 2. llvm-profdata 工具路径
#    必须与 rustc 版本匹配，通常在 build/host/llvm/bin/ 下
PROFDATA_TOOL = "/home/lulan/MyProjects/rustc-fuzz/rust/build/host/ci-llvm/bin/llvm-profdata"

# 3. 需要扫描的源代码目录
SOURCE_DIR = "code_gen"

# 4. 覆盖率文件临时输出目录 (Fuzzer 吐出的 raw 文件放这里)
COVERAGE_INCOMING_DIR = "coverage_incoming"

# 5. 最终合并的索引文件路径
FINAL_PROFDATA = "fuzzing_total.profdata"

# 6. 记录已处理过的文件列表
RECORD_FILE = "compiled_done.txt"

# 7. 批次大小：累积多少个 .profraw 文件后执行一次合并清理
BATCH_SIZE = 20

# 8. 【新增】单文件编译超时时间 (秒)
#    防止 rustc 因死循环或极度复杂的类型推导而卡死
TIMEOUT_SEC = 30

# LLVM_PROFILE_FILE 模式 (%p=pid, %m=signature)
PROFILE_PATTERN = os.path.join(os.path.abspath(COVERAGE_INCOMING_DIR), "cov_%p_%m.profraw")

# ===========================================

def load_processed_files():
    """读取已处理的文件列表"""
    processed = set()
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    processed.add(line.strip())
        except Exception as e:
            print(f"Warning: 读取记录文件失败: {e}")
    return processed

def perform_merge_and_clean():
    """
    核心功能：扫描临时目录，合并 profraw 到 profdata，然后删除 profraw
    """
    # 扫描所有 .profraw 文件
    profraw_files = glob.glob(os.path.join(COVERAGE_INCOMING_DIR, "*.profraw"))
    
    if not profraw_files:
        return

    # 为了防止打印刷屏，这里用覆盖行的方式显示状态
    print(f"\r[Merge] 正在合并 {len(profraw_files)} 个覆盖率文件...", end="", flush=True)

    # 构建命令: llvm-profdata merge -sparse -o total.profdata [existing.profdata] [new files...]
    cmd = [PROFDATA_TOOL, "merge", "-sparse"]
    
    # 增量更新：如果总表存在，必须把它加进去
    if os.path.exists(FINAL_PROFDATA):
        cmd.append(FINAL_PROFDATA)
    
    cmd.extend(profraw_files)
    cmd.extend(["-o", FINAL_PROFDATA])

    try:
        # 执行合并
        subprocess.run(cmd, check=True, capture_output=True)
        
        # 合并成功后，删除原始 raw 文件以释放磁盘空间
        for f in profraw_files:
            try:
                os.remove(f)
            except OSError:
                pass
        
        # 计算当前总大小
        current_size_mb = os.path.getsize(FINAL_PROFDATA) / (1024 * 1024)
        print(f"\r[Merge] 合并成功 (总大小: {current_size_mb:.2f} MB) - 已清理临时文件    ", flush=True)
        print("") # 换行

    except subprocess.CalledProcessError as e:
        print(f"\n[Error] 合并失败: {e}")

def main():
    # 1. 基础检查
    if not os.path.isfile(RUSTC_BIN):
        print(f"Error: 编译器未找到: {RUSTC_BIN}")
        sys.exit(1)
    if not os.path.isfile(PROFDATA_TOOL) and shutil.which(PROFDATA_TOOL) is None:
        print(f"Error: llvm-profdata 工具未找到: {PROFDATA_TOOL}")
        sys.exit(1)
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: 源代码目录未找到: {SOURCE_DIR}")
        sys.exit(1)

    # 确保目录存在
    os.makedirs(COVERAGE_INCOMING_DIR, exist_ok=True)

    # 2. 加载进度
    processed_set = load_processed_files()
    print(f"此前已处理文件数: {len(processed_set)}")

    # 3. 设置环境变量
    env = os.environ.copy()
    env["LLVM_PROFILE_FILE"] = PROFILE_PATTERN

    print(f"开始扫描 '{SOURCE_DIR}' (超时设定: {TIMEOUT_SEC}s) ...")
    
    count_new_processed = 0
    count_skipped = 0
    
    stat_ok = 0
    stat_fail = 0
    stat_timeout = 0

    # 打开记录文件
    with open(RECORD_FILE, 'a', encoding='utf-8', buffering=1) as record_f:
        for root, dirs, files in os.walk(SOURCE_DIR):
            for file in files:
                if file.endswith(".rs"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, start=".")

                    # --- 检查跳过 ---
                    if rel_path in processed_set:
                        count_skipped += 1
                        continue

                    # --- 执行编译 ---
                    with tempfile.TemporaryDirectory() as temp_out_dir:
                        cmd = [RUSTC_BIN, full_path, "--out-dir", temp_out_dir]
                        
                        # 【关键】先打印正在跑哪个文件，这样卡住时你就知道是谁干的
                        # 使用相对路径并截断过长的文件名，保持界面整洁
                        display_name = rel_path if len(rel_path) < 60 else "..." + rel_path[-57:]
                        print(f"\r[RUN] {display_name:<60}", end="", flush=True)

                        try:
                            # 【关键】设置 timeout，防止死循环卡死脚本
                            result = subprocess.run(
                                cmd, 
                                env=env, 
                                check=False, 
                                capture_output=True, 
                                text=True,
                                timeout=TIMEOUT_SEC # <--- 粗暴的超时强制结束
                            )
                            
                            # --- 记录处理完成 ---
                            record_f.write(rel_path + "\n")
                            processed_set.add(rel_path)
                            count_new_processed += 1
                            
                            if result.returncode == 0:
                                print(f"\r[OK]  {display_name:<60}")
                                stat_ok += 1
                            else:
                                print(f"\r[FAIL] {display_name:<60} (Code: {result.returncode})")
                                stat_fail += 1

                        except subprocess.TimeoutExpired:
                            # --- 处理超时情况 ---
                            print(f"\r[TIME] {display_name:<60}")
                            stat_timeout += 1
                            
                            # 超时也算处理过了（避免下次无限重试同一个文件）
                            record_f.write(rel_path + "\n")
                            processed_set.add(rel_path)
                            count_new_processed += 1
                            
                        except Exception as e:
                            print(f"\n[ERR]  脚本执行异常 {rel_path}: {e}")

                    # --- 批次处理逻辑 ---
                    # 检查 coverage 目录下的 profraw 文件数量
                    try:
                        # 简单的 glob 计数
                        current_profraws_len = len(glob.glob(os.path.join(COVERAGE_INCOMING_DIR, "*.profraw")))
                        if current_profraws_len >= BATCH_SIZE:
                            perform_merge_and_clean()
                    except Exception:
                        pass

    # 4. 收尾工作
    print("\n[Finalizing] 处理剩余的覆盖率数据...")
    perform_merge_and_clean()

    print("\n" + "="*30)
    print(f"全部完成。")
    print(f"本次新处理: {count_new_processed}")
    print(f"  - 成功: {stat_ok}")
    print(f"  - 失败: {stat_fail} (rustc 报错)")
    print(f"  - 超时: {stat_timeout} (> {TIMEOUT_SEC}s)")
    print(f"跳过已处理: {count_skipped}")
    print(f"最终索引文件: {os.path.abspath(FINAL_PROFDATA)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Stop] 用户手动停止脚本。")