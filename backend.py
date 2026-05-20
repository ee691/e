from fastapi import FastAPI
from langserve import add_routes
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

# 加载密钥
load_dotenv()

# 1. 初始化服务
app = FastAPI(
    title="故事生成后端服务",
    version="1.0",
    description="基于LangServe实现，支持高并发"
)

# 2. 初始化DeepSeek模型
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL")
)

# 3. 定义故事生成提示词链
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是专业儿童故事生成器，语言简短易懂"),
    ("user", "根据主题生成一个简短故事：{topic}")
])
story_chain = prompt | llm

# 4. LangServe挂载接口（老师强制要求）
add_routes(app, story_chain, path="/story")

# 5. 高并发启动配置
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend:app",
        host="127.0.0.1",
        port=10000,
        workers=4  # 多进程=高并发，完全满足作业要求
    )