import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载 .env 文件
load_dotenv()

def get_llm():
    """获取配置好的 LLM 实例"""
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME"),
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base=os.getenv("DEEPSEEK_BASE_URL"),
        temperature=0.1  # 保持低温，确保代码生成精确
    )