import requests
import os
import re
from datetime import datetime

# 配置参数
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  # 替换为你的GitHub token
REPO_OWNER = "rust-lang"
REPO_NAME = "rust"
MAX_ISSUES = 50  # 可自定义数量
OUTPUT_DIR = "output"

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# GitHub API请求头
headers = {
    "Accept": "application/vnd.github.v3+json",
}

if GITHUB_TOKEN:
    headers["Authorization"] = f"token {GITHUB_TOKEN}"

# 构建API请求URL
url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"

# 构建查询参数
params = {
    "labels": "T-compiler,I-ICE",
    "state": "all",
    "per_page": 100,  # 每页最多100个issue
    "sort": "created",
    "direction": "desc"
}

# 用于存储所有符合条件的issue
issues = []

# 分页获取issue
page = 1
while len(issues) < MAX_ISSUES:
    params["page"] = page
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # 检查请求是否成功
    
    page_issues = response.json()
    if not page_issues:
        break  # 没有更多issue了
    
    # 筛选带有T-compiler和I-ICE标签的issue
    for issue in page_issues:
        if len(issues) >= MAX_ISSUES:
            break
        
        # 检查issue是否同时包含T-compiler和I-ICE标签
        labels = [label["name"] for label in issue.get("labels", [])]
        if "T-compiler" in labels and "I-ICE" in labels:
            issues.append(issue)
    
    page += 1

# 处理每个issue
def extract_code_and_output(body):
    """从issue body中提取代码和编译器输出"""
    # 匹配Rust代码块
    code_blocks = re.findall(r'```rust[\s\S]*?```', body)
    # 匹配编译器输出块（通常是没有语言指定的代码块）
    output_blocks = re.findall(r'```[\s\S]*?```', body)
    
    # 尝试区分代码和输出
    trigger_code = ""
    compiler_output = ""
    
    # 优先选择第一个Rust代码块作为trigger code
    for block in code_blocks:
        # 移除代码块标记
        code = block.strip('```rust').strip()
        if code:
            trigger_code = code
            break
    
    # 尝试找到编译器输出
    for block in output_blocks:
        # 移除代码块标记
        output = block.strip('```').strip()
        # 检查是否包含编译器错误信息
        if any(keyword in output for keyword in ["error:", "internal compiler error", "rustc"]):
            compiler_output = output
            break
    
    return trigger_code, compiler_output

# 处理每个issue
for issue in issues:
    issue_number = issue.get("number")
    issue_title = issue.get("title")
    issue_body = issue.get("body", "")
    
    # 提取代码和编译器输出
    trigger_code, compiler_output = extract_code_and_output(issue_body)
    
    # 生成markdown文件
    if trigger_code and compiler_output:
        markdown_content = f"# Issue #{issue_number}: {issue_title}\n\n"
        markdown_content += "## Trigger Code\n\n"
        markdown_content += f"```rust\n{trigger_code}\n```\n\n"
        markdown_content += "## Compiler Output\n\n"
        markdown_content += f"```\n{compiler_output}\n```\n"
        
        # 保存到文件
        output_file = os.path.join(OUTPUT_DIR, f"issue_{issue_number}.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        print(f"Saved issue #{issue_number} to {output_file}")
    else:
        print(f"Skipped issue #{issue_number} - no code or compiler output found")

print(f"\nProcessed {len(issues)} issues")