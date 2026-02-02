import datetime
import os

class HistoryLogger:
    """
    辅助类：用于收集和保存运行历史
    功能：
    - 记录日志信息
    - 记录失败尝试（Diffs）
    - 保存最终结果
    - 将所有信息写入文件
    """
    def __init__(self):
        self.logs = []
        self.failed_attempts = []
        self.final_code = None
        self.start_time = datetime.datetime.now()

    def add_log(self, message: str):
        """添加日志消息并打印到控制台"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.logs.append(formatted_msg)

    def add_failed_diff(self, diff: str):
        """记录失败尝试的 Diff"""
        self.failed_attempts.append(diff)

    def set_final_code(self, code: str):
        """设置最终结果代码"""
        self.final_code = code

    def save_to_file(self, filename1: str, filename2: str):
        """将收集到的所有信息写入日志文件"""
        duration = datetime.datetime.now() - self.start_time
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename1) or ".", exist_ok=True)

        # 记录完整日志
        with open(filename1, "w", encoding="utf-8") as f:
            # 1. 头部信息
            f.write("="*60 + "\n")
            f.write("RUST ICE AGENT EXECUTION LOG\n")
            f.write(f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {duration}\n")
            f.write("="*60 + "\n\n")

            # 2. 执行日志
            f.write(">>> EXECUTION LOGS <<<\n")
            f.write("-" * 30 + "\n")
            for log in self.logs:
                f.write(log + "\n")
            f.write("\n")
        
        # 记录失败尝试到单独文件
        with open(filename2, "w", encoding="utf-8") as f:
            f.write(f">>> FAILED ATTEMPTS (Total: {len(self.failed_attempts)}) <<<\n")
            f.write("-" * 30 + "\n")
            if not self.failed_attempts:
                f.write("(No failed attempts recorded)\n")
            else:
                for i, diff in enumerate(self.failed_attempts, 1):
                    f.write(f"\n[Attempt #{i} Failed Diff]:\n")
                    f.write("```diff\n")
                    f.write(diff)
                    f.write("\n```\n")
            f.write("\n")
