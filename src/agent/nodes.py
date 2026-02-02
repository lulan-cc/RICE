from asyncio import as_completed
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from langchain_core.messages import HumanMessage

from config import get_llm
from agent.state import AgentState
from tools.parser import parse_markdown_input
from tools.compiler import run_compiler, check_is_ice, setup_compiler_env
from tools.diff import get_concise_diff
from tools.ast import match_and_save


llm = get_llm()

def parse_input_node(state: AgentState):
    doc = state.get("input_doc", "")
    parsed = parse_markdown_input(doc)
    
    setup_compiler_env(parsed["commit"])

    return {
        "original_code": parsed["code"],
        "current_code": parsed["code"],
        "best_code": parsed["code"],
        "compiler_commit": parsed["commit"],
        "failed_attempts": [],
        "iteration": 0,
        "consecutive_failure_count": 0,
        "logs": [f"Initialized. Target Commit: {parsed['commit'][:8]}"]
    }

def minifier_node(state: AgentState):
    current_best = state["best_code"]
    failed_diffs = state["failed_attempts"]
    compiler_output = state.get("compiler_output", "")
    status = state.get("status", "unknown")
    
    history_section = ""
    if failed_diffs:
        history_section = "### PREVIOUS FAILED SIMPLIFICATIONS (When the following operations were performed, the crash disappeared - AVOID DO THESE SIMPLIFICATIONS):\n"
        # 取最近 5 次
        for i, diff in enumerate(failed_diffs[-5:]):
            history_section += f"Attempt {i+1} Diff:\n```diff\n{diff}\n```\n\n"

    prompt = f"""
    You are a Rust compiler expert minimizing a reproduction code snippet for an Internal Compiler Error (ICE).
    
    OBJECTIVE:  Minimize code size by descreasing the token numbers while preserving the compiler crash in the compiler output. You don't have to completely preserve the semantics of the current code.
    
    CURRENT CODE:
    ```rust
    {current_best}
    ```

    COMPILER OUTPUT:
    ```
    {compiler_output}
    ```

    {history_section}

    LAST SIMPLIFICATION STATUS: {status}

    STRATEGY:
    - If the last simplification status was success, please proceed to try a more aggressive simplification strategy.
    - If the last simplification status was failure, please attempt a conservative simplification strategy.
    
    OUTPUT FORMAT:
    1. A single line describes EXACTLY what you removed or changed (e.g., "Removed unused struct `Foo`").
    2. The full minimized Rust code in a ```rust``` block.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    
    new_code_match = re.search(r"```rust(.*?)```", content, re.DOTALL)
    new_code = new_code_match.group(1).strip() if new_code_match else current_best
    
    summary = content.split('\n')[0].strip()
    
    return {
        "current_code": new_code,
        "iteration": state["iteration"] + 1,
        "logs": [f"Iter {state['iteration'] + 1}: {summary}"]
    }

def verification_node(state: AgentState):
    code = state["current_code"]
    output = run_compiler(code)
    
    if check_is_ice(output):
        # 计算成功的 Diff，方便用户查看做了什么改动
        reduction_count = len(state["best_code"]) - len(code)
        success_diff = get_concise_diff(state["best_code"], code)
        
        # 构建更详细的日志
        log_msg = f"✅ Verification Passed! Reduced {reduction_count} chars."
        if success_diff.strip():
            log_msg += f"\n>>> Successful Change Diff:\n{success_diff}"
        
        return {
            "consecutive_failure_count": 0,
            "best_code": code,
            "status": "success",
            "logs": [log_msg]
        }
    else:
        diff = get_concise_diff(state["best_code"], code)
        log_msg = f"❌ Simplification Failed!"
        if diff.strip():
            log_msg += f"\n>>> Failed Change Diff:\n{diff}"
            return {
                "consecutive_failure_count": state["consecutive_failure_count"] + 1,
                "failed_attempts": [log_msg],
                "status": "failure",
                "logs": [log_msg]
            }
        return {
            "status": "failed",
            "logs": ["Verification Failed: No diff."]
        }
    
def reasoner_node(state: AgentState):
    # 分析缺陷诱发模式
    simplified_triggering_code = state["best_code"]
    compiler_output = state.get("compiler_output", "")
    key_operations = "\n".join(state.get("failed_attempts", []))
    prompt = f"""
    You are an expert in researching Rust compiler ICE (Internal Compiler Error) bugs, with exceptional skill in identifying the core code patterns that trigger ICEs in the Rust compiler.

    OBJECTIVE: Combining the compiler crash output and key operations,
    extract the minimal defect-prone code pattern that cause the compiler crash from the simplified defect-triggering code. 

    SIMPLIFIED DEFECT-TRIGGERING CODE:
    {simplified_triggering_code}

    COMPILER OUTPUT:
    {compiler_output}

    KEY OPERATIONS(When the following actions are performed, the crash disappears):
    {key_operations}

    OUTPUT FORMAT(Strictly follow the format below when outputting. Do not output any other extra content):
    Defect-Prone Code Pattern
    ```rust
    <Core defect-prone code snippets in triggering code>
    ```
    Defect Code Pattern Characteristics
    <Describe key characteristics of defect-prone code pattern>
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    
    return {
        "defect_prone": content,
        "logs": ["🧠 Reasoning completed: Defect-prone pattern identified.\n" + content]
    }

def filter_node(state: AgentState):
    defect_prone_info = state.get("defect_prone", "No defect-prone pattern identified.")
    defect_prone_code = re.search(r"```rust(.*?)```", defect_prone_info, re.DOTALL)
    defect_code = defect_prone_code.group(1).strip() if defect_prone_code else ""

    input_dir = "../rust/tests/ui"
    output_dir = os.path.join("output", state["issue_id"], "matched_cases")

    # 遍历 ../rust/tests/ui 目录下的所有 .rs 文件，进行匹配和保存
    for root, dirs, files in os.walk(input_dir):
        for file_name in files:
            if file_name.endswith(".rs"):
                file_path = os.path.join(root, file_name)

                # 读取文件内容
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                except Exception as e:
                    print(f"无法读取文件 {file_path}: {e}")
                    continue

                # 构造输出文件路径，保持原目录结构
                rel_path = os.path.relpath(file_path, input_dir)
                save_path = os.path.join(output_dir, rel_path)

                # 调用工具函数进行匹配
                matched = match_and_save(defect_code, code, save_path, threshold=0.6)
                if matched:
                    print(f"[MATCHED] {file_path} -> 保存到 {save_path}")
                else:
                    print(f"[NO MATCH] {file_path}")
    return {
        "logs": ["🔍 Filtering completed: Matched test cases saved."]
    }

def mutator_node(state: AgentState):
    # 变异缺陷诱发代码以生成新的测试用例
    defect_prone_info = state.get("defect_prone", "No defect-prone pattern identified.")

    # 遍历 output/<issue_id>/matched_cases/ 目录下的所有 .rs 文件，进行变异
    input_dir = os.path.join("output", state["issue_id"], "matched_cases")
    target_code = ""
    for root, _, files in os.walk(input_dir):
        for file_name in files:
            if file_name.endswith(".rs"):
                file_path = os.path.join(root, file_name)

                with open(file_path, "r", encoding="utf-8") as f:
                    target_code = f.read()
                    prompt = f"""
OBJECTIVE: Based on the description in the "DEFECT-PRONE CODE PATTERN CHARACTERISTICS", refactor the "TARGET CODE" so that it possesses similar features to the "DEFECT-PRONE CODE PATTERN".

{defect_prone_info}

TARGET CODE:
```rust
{target_code}
```

OUTPUT FORMAT(Strictly follow the format below when outputting. Do not output any other extra content):
Mutated Code
```rust
<Full mutated target code>
```
                    """
                    # 提取filename的前缀
                    file_name_pre = os.path.splitext(file_name)[0]
                    prompt_path = os.path.join("output", state["issue_id"], "mutation_prompts", f"{file_name_pre}.txt")
                    os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
                    with open(prompt_path, "w", encoding="utf-8") as f:
                        f.write(prompt)

    
    # 正则匹配 ```rust ... ```
    RUST_CODE_RE = re.compile(r"```rust\s*(.*?)```", re.DOTALL | re.IGNORECASE)

    async def invoke_llm(file_path):
        """线程池中执行 LLM 并返回 (file_path, rust_code_output)"""
        loop = asyncio.get_event_loop()

        def _call():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    prompt = f.read()
                llm_output = llm.invoke([HumanMessage(content=prompt)])
                # 提取 ```rust ... ``` 中的内容
                matches = RUST_CODE_RE.findall(str(llm_output))
                rust_code = "\n".join(matches).strip()
                return file_path, rust_code
            except Exception as e:
                return file_path, f"Error: {e}"

        return await loop.run_in_executor(executor, _call)

    async def run():
        base_dir = os.path.join("output", state["issue_id"], "mutation_prompts")
        if not os.path.exists(base_dir):
            print(f"目录不存在: {base_dir}")
            return

        # 收集所有 .txt 文件
        txt_files = []
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith(".txt"):
                    txt_files.append(os.path.join(root, f))

        print(f"找到 {len(txt_files)} 个 .txt 文件")

        nonlocal executor
        executor = ThreadPoolExecutor(max_workers=8)

        # 异步任务列表
        tasks = [invoke_llm(f) for f in txt_files]

        for future in asyncio.as_completed(tasks):
            file_path, rust_code = await future
            print(f"[DONE] {file_path}")

            rust_code_real = rust_code.replace("\\n", "\n")

            # 构建输出文件路径：保持相对目录，文件名后缀改为 .rs
            rel_path = os.path.relpath(file_path, base_dir)
            rel_path_rs = os.path.splitext(rel_path)[0] + ".rs"  # 改后缀为 .rs
            out_path = os.path.join("output", state["issue_id"], "mutated_cases", rel_path_rs)

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rust_code_real)

    executor = None
    asyncio.run(run())

    return {
        "logs": ["🧬 Mutation completed: New test cases generated."]
    }

def detector_node(state: AgentState):
    # 对变异生成的测试用例进行检测，找出新的 ICE 触发用例
    input_dir = os.path.join("output", state["issue_id"], "mutated_cases")
    output_dir = os.path.join("pending_review", "ice")
    os.makedirs(output_dir, exist_ok=True)

    def compile_rust_file(file_path: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = subprocess.run(
                    ["rustc", "+nightly", file_path, "--out-dir", tmpdir],
                    capture_output=True,
                    text=True
                )
                return result.stdout + "\n" + result.stderr
            except Exception as e:
                return str(e)

    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".rs"):
                file_path = os.path.join(root, file)
                print(f"Compiling {file_path} ...")
                output = compile_rust_file(file_path)
                if check_is_ice(output):
                    print(f"ICE detected in {file}, saving to {output_dir}")
                    shutil.copy(file_path, output_dir)

    return {
        "logs": ["🕵️‍♂️ Detection completed"]
    }