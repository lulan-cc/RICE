import re
from typing import Dict

def parse_markdown_input(doc: str) -> Dict[str, str]:
    """解析输入的 Markdown 文档"""
    code_match = re.search(r"## Trigger Code\s+```rust(.*?)```", doc, re.DOTALL)
    if not code_match:
        raise ValueError("No trigger code found")
    version_match = re.search(r"rustc .* \(([0-9a-fA-F]+)", doc)
    if not version_match:
        raise ValueError("No compiler version found")
    compiler_output_match = re.search(r"## Compiler Output\s+```(.*?)```", doc, re.DOTALL)
    if not compiler_output_match:
        raise ValueError("No compiler output found")
    
    return {
        "code": code_match.group(1).strip() if code_match else "",
        "commit": version_match.group(1).strip() if version_match else "nightly",
        "compiler_output": compiler_output_match.group(1).strip() if compiler_output_match else ""
    }