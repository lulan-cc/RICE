import subprocess
import os

def check_is_ice(compiler_output: str) -> bool:
    """通过关键词判断是否复现了 ICE"""
    keywords = [
        "thread 'rustc' panicked",
        "internal compiler error",
        "unexpectedly panicked",
        "query stack during panic"
    ]
    lower_output = compiler_output.lower()
    return any(k.lower() in lower_output for k in keywords)

def setup_compiler_env(commit_hash: str):
    """
    构建特定 Commit 的编译器环境。
    """
    print(f"Building rustc for commit {commit_hash}...")
    # 克隆 github rust 仓库，先检查 ../rust 是否存在
    if not os.path.exists("../rust"):
        cmd_clone = ["git", "clone", "https://github.com/rust-lang/rust.git", "../rust"]
        subprocess.run(cmd_clone, check=True)
    # 切换到指定 commit 并构建
    os.chdir("../rust")
    cmd_checkout = ["git", "checkout", commit_hash]
    subprocess.run(cmd_checkout, check=True)
    cmd_setup = ["./x.py", "setup"]
    subprocess.run(cmd_setup, check=True)
    cmd_build = ["./x.py", "build"]
    subprocess.run(cmd_build, check=True)
    os.chdir("../src")

def run_compiler(code: str) -> str:
    """
    运行编译器。
    """
    filename = "output/tmp.rs"
    os.makedirs("output", exist_ok=True)
    with open(filename, "w") as f:
        f.write(code)

    cmd = ["rustc", "+stage1", filename]
    # cmd = ["rustc", filename]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stderr + result.stdout