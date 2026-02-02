from typing import TypedDict, List, Annotated
import operator

class AgentState(TypedDict):
    input_doc: str
    issue_id: str
    original_code: str
    current_code: str
    best_code: str
    compiler_commit: str
    compiler_output: str
    
    # 记忆模块：使用 operator.add 实现增量更新
    failed_attempts: Annotated[List[str], operator.add]
    
    iteration: int
    consecutive_failure_count: int
    status: str
    logs: Annotated[List[str], operator.add]
    defect_prone: str