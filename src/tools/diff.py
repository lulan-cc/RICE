import difflib

def get_concise_diff(original_code: str, modified_code: str) -> str:
    """
    生成两个代码片段之间的精简 Diff。
    只保留差异行，去除文件名头信息。
    """
    diff = difflib.unified_diff(
        original_code.splitlines(),
        modified_code.splitlines(),
        lineterm=""
    )
    
    clean_diff = []
    for line in diff:
        if line.startswith(('---', '+++', '@@')):
            continue
        clean_diff.append(line)
    
    return "\n".join(clean_diff)