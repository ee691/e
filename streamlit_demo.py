import streamlit as st
from datetime import datetime
import hashlib
import os
import json
import io
import base64
import requests

# ========================== 核心依赖检查 ==========================
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    
if not OPENAI_AVAILABLE:
    st.error("⚠️ 缺少必要依赖：openai 库")
    st.info("请安装依赖：pip install openai")
    st.stop()
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None
    ChatPromptTemplate = None
    StrOutputParser = None
import time
import sqlite3

# ========================== 云端环境适配 ==========================
# 检查是否在云端环境（通过环境变量判断）
IS_CLOUD_ENV = os.getenv('STREAMLIT_SHARING_URL') is not None or os.getenv('VERCEL') is not None or os.getenv('RENDER') is not None

# 尝试导入可选依赖
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    Image = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    canvas = None
    A4 = (612, 792)  # 默认 A4 尺寸

# 图片转 base64（支持本地文件和远程 URL）
def get_base64(source):
    """
    将图片转换为 base64 编码
    :param source: 本地文件路径或远程图片 URL
    :return: base64 编码字符串
    """
    try:
        # 判断是否为 URL
        if source.startswith('http://') or source.startswith('https://'):
            # 远程图片：下载并转换
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            return base64.b64encode(response.content).decode()
        else:
            # 本地文件
            with open(source, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception as e:
        st.warning(f"无法加载图片 {source}: {str(e)}")
        return ""

# 图片压缩函数
def compress_image(image_data, max_size_kb=100, quality=80, max_dimension=512):
    """
    压缩图片到指定大小
    :param image_data: 原始图片数据（bytes）
    :param max_size_kb: 最大大小（KB）
    :param quality: 压缩质量（1-100）
    :param max_dimension: 最大尺寸（像素）
    :return: 压缩后的图片数据（bytes）
    """
    if not PILLOW_AVAILABLE:
        return image_data
    
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # 调整尺寸
        width, height = img.size
        max_dim = max(width, height)
        if max_dim > max_dimension:
            ratio = max_dimension / max_dim
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 如果是 PNG 格式，转换为 RGB（JPEG不支持透明）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 逐步压缩直到满足大小要求
        current_quality = quality
        while current_quality >= 10:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=current_quality)
            compressed_data = buffer.getvalue()
            
            if len(compressed_data) / 1024 <= max_size_kb:
                return compressed_data
            
            current_quality -= 10
        
        # 如果压缩到最低质量仍太大，返回原始数据
        return image_data
    except Exception as e:
        st.warning(f"图片压缩失败，将使用原始图片: {str(e)}")
        return image_data

# 生成响应式图片 HTML
def get_responsive_image_html(image_base64, content_type, max_width="200px"):
    """
    生成响应式图片的 HTML
    :param image_base64: base64 编码的图片数据
    :param content_type: 图片类型（如 image/jpeg）
    :param max_width: 最大宽度
    :return: HTML 字符串
    """
    return f'''
    <img src="data:{content_type};base64,{image_base64}" 
         style="max-width: {max_width}; width: 100%; height: auto; object-fit: cover; border-radius: 50%;" 
         alt="头像" />
    '''

# 4 个主题 4 张图
bg1 = get_base64("4.jpg")
bg2 = get_base64("1.1.jpeg")
bg3 = get_base64("1.2.png")
bg4 = get_base64("1.3.png")


# ========================== 数据持久化（云端适配 - SQLite） ==========================
DATA_FILE = "app_data.json"
DB_FILE = "story_app.db"

def init_database():
    """初始化 SQLite 数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 创建故事历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            keyword TEXT NOT NULL,
            style TEXT NOT NULL,
            content TEXT NOT NULL,
            time TEXT NOT NULL,
            language TEXT,
            image_url TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    # 创建收藏表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            story_id INTEGER NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (story_id) REFERENCES story_history(id)
        )
    ''')
    
    # 创建点赞表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            story_time TEXT NOT NULL,
            UNIQUE(username, story_time)
        )
    ''')
    
    # 创建每日计数表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_count (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            UNIQUE(username, date)
        )
    ''')
    
    # 创建用户资料表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            username TEXT PRIMARY KEY,
            nickname TEXT,
            avatar TEXT,
            bio TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    conn.commit()
    conn.close()

def init_empty_data():
    return {
        "users": {},
        "story_history": [],
        "favorite_stories": [],
        "story_likes": [],
        "daily_count": {},
        "user_profiles": {}
    }

def load_data():
    """加载数据：云端使用 SQLite，本地使用 JSON 文件"""
    if IS_CLOUD_ENV:
        # 云端环境：从 SQLite 数据库加载
        init_database()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        data = init_empty_data()
        
        # 加载用户
        cursor.execute("SELECT username, password, created_at FROM users")
        for row in cursor.fetchall():
            data["users"][row[0]] = {"password": row[1], "created_at": row[2]}
        
        # 加载故事历史
        cursor.execute("SELECT keyword, style, content, time, language, image_url, username FROM story_history ORDER BY id DESC")
        for row in cursor.fetchall():
            data["story_history"].append({
                "keyword": row[0],
                "style": row[1],
                "content": row[2],
                "time": row[3],
                "language": row[4] if row[4] else "中文",
                "image_url": row[5],
                "username": row[6]
            })
        
        # 加载收藏
        cursor.execute("SELECT keyword, style, content, time, language, image_url FROM story_history WHERE id IN (SELECT story_id FROM favorites)")
        for row in cursor.fetchall():
            data["favorite_stories"].append({
                "keyword": row[0],
                "style": row[1],
                "content": row[2],
                "time": row[3],
                "language": row[4] if row[4] else "中文",
                "image_url": row[5]
            })
        
        # 加载点赞
        cursor.execute("SELECT story_time FROM likes")
        data["story_likes"] = [row[0] for row in cursor.fetchall()]
        
        # 加载每日计数
        cursor.execute("SELECT username, date, count FROM daily_count")
        for row in cursor.fetchall():
            key = f"{row[0]}_{row[1]}"
            data["daily_count"][key] = row[2]
        
        # 加载用户资料
        cursor.execute("SELECT username, nickname, avatar, bio FROM user_profiles")
        for row in cursor.fetchall():
            data["user_profiles"][row[0]] = {
                "nickname": row[1],
                "avatar": row[2],
                "bio": row[3]
            }
        
        conn.close()
        return data
    else:
        # 本地环境：使用 JSON 文件
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return init_empty_data()
        return init_empty_data()

def save_data(data):
    """保存数据：云端使用 SQLite，本地使用 JSON 文件"""
    if IS_CLOUD_ENV:
        # 云端环境：保存到 SQLite 数据库
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 保存用户
        cursor.execute("DELETE FROM users")
        for username, user_info in data["users"].items():
            cursor.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, user_info["password"], user_info.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            )
        
        # 保存故事历史
        cursor.execute("DELETE FROM story_history")
        for story in data["story_history"]:
            cursor.execute(
                "INSERT INTO story_history (keyword, style, content, time, language, image_url, username) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (story["keyword"], story["style"], story["content"], story["time"], 
                 story.get("language", "中文"), story.get("image_url"), story.get("username", ""))
            )
        
        # 保存收藏
        cursor.execute("DELETE FROM favorites")
        for idx, story in enumerate(data["favorite_stories"]):
            cursor.execute(
                "INSERT INTO favorites (username, story_id) VALUES (?, ?)",
                (story.get("username", ""), idx + 1)
            )
        
        # 保存点赞
        cursor.execute("DELETE FROM likes")
        for story_time in data["story_likes"]:
            cursor.execute(
                "INSERT INTO likes (username, story_time) VALUES (?, ?)",
                ("", story_time)
            )
        
        # 保存每日计数
        cursor.execute("DELETE FROM daily_count")
        for key, count in data["daily_count"].items():
            parts = key.split("_")
            if len(parts) == 2:
                cursor.execute(
                    "INSERT INTO daily_count (username, date, count) VALUES (?, ?, ?)",
                    (parts[0], parts[1], count)
                )
        
        # 保存用户资料
        cursor.execute("DELETE FROM user_profiles")
        for username, profile in data["user_profiles"].items():
            cursor.execute(
                "INSERT INTO user_profiles (username, nickname, avatar, bio) VALUES (?, ?, ?, ?)",
                (username, profile.get("nickname", ""), profile.get("avatar", ""), profile.get("bio", ""))
            )
        
        conn.commit()
        conn.close()
    else:
        # 本地环境：保存到 JSON 文件
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

app_data = load_data()

# ========================== 读取 API 密钥（云端适配） ==========================
# 云端环境直接使用环境变量，本地环境使用 .env 文件
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

if not IS_CLOUD_ENV and DOTENV_AVAILABLE:
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path)
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

if not API_KEY:
    st.error("⚠️ 未读取到 API 密钥，请在环境变量中设置 DEEPSEEK_API_KEY")
    st.info("本地开发：请在项目根目录创建 .env 文件，添加 DEEPSEEK_API_KEY=你的密钥")
    st.info("云端部署：请在部署平台的环境变量中设置 DEEPSEEK_API_KEY")
    st.stop()

# LangSmith 监控配置（可选）
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "story-creator")

ai_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ========================== LangChain 创意写作助手（增强版：Memory + Tool + Agent） ==========================
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.output_parsers import StrOutputParser
    from langchain.memory import ConversationBufferMemory
    from langchain_core.tools import tool
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None
    ChatPromptTemplate = None
    StrOutputParser = None
    ConversationBufferMemory = None
    tool = None
    create_openai_tools_agent = None
    AgentExecutor = None

if LANGCHAIN_AVAILABLE:
    # ------------------------------ 1. 定义字数统计工具 ------------------------------
    @tool
    def count_words(text: str) -> int:
        """
        统计文本总字数
        :param text: 要统计的文本
        :return: 字数
        """
        return len(text.strip())

    @tool
    def check_word_limit(text: str, max_words: int) -> str:
        """
        检查是否超过字数限制
        :param text: 故事文本
        :param max_words: 最大允许字数
        :return: 检查结果
        """
        count = len(text.strip())
        if count > max_words:
            return f"超出字数限制！当前{count}字，要求{max_words}字"
        else:
            return f"字数合规！当前{count}字，要求{max_words}字"

    tools = [count_words, check_word_limit]

    # ------------------------------ 2. 全局对话记忆 ------------------------------
    story_memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    # ------------------------------ 3. 创建带记忆+工具的创作链 ------------------------------
    def create_story_chain():
        llm = ChatOpenAI(
            temperature=0.7,
            model="deepseek-chat",
            base_url=BASE_URL,
            api_key=API_KEY
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是专业的故事创作助手，会严格控制字数，并使用工具统计字数、检查字数限制。"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", """
创作要求：
- 故事主题：{keyword}
- 故事风格：{style}
- 情绪氛围：{emotion}
- 心情基调：{mood}
- 语言：{language}
- 字数要求：{word_count}字

请直接输出故事，不要标题和多余说明。
"""),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=story_memory,
            verbose=False,
            max_iterations=2
        )
        return agent_executor

    # ------------------------------ 4. 生成故事（带记忆+工具调用） ------------------------------
    def generate_story_with_langchain(keyword, style, emotion, mood, language, word_count):
        try:
            from langchain.callbacks import get_openai_callback
            agent = create_story_chain()

            with get_openai_callback() as cb:
                result = agent.invoke({
                    "keyword": keyword,
                    "style": style,
                    "emotion": emotion,
                    "mood": mood,
                    "language": language,
                    "word_count": word_count
                })
                total_tokens = cb.total_tokens
                total_cost = cb.total_cost

            if "usage_stats" not in st.session_state:
                st.session_state.usage_stats = {"total_tokens": 0, "total_cost": 0, "story_count": 0}

            st.session_state.usage_stats["total_tokens"] += total_tokens
            st.session_state.usage_stats["total_cost"] += total_cost
            st.session_state.usage_stats["story_count"] += 1

            return result["output"]

        except Exception as e:
            print(f"LangChain 增强模式异常：{str(e)}")
            return None
else:
    def generate_story_with_langchain(keyword, style, emotion, mood, language, word_count):
        return None

# ========================== 初始化会话状态 ==========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "story_history" not in st.session_state:
    st.session_state.story_history = app_data["story_history"]
if "favorite_stories" not in st.session_state:
    st.session_state.favorite_stories = app_data["favorite_stories"]
if "users" not in st.session_state:
    st.session_state.users = app_data["users"]
if "current_story" not in st.session_state:
    st.session_state.current_story = None
if "editing_story" not in st.session_state:
    st.session_state.editing_story = False
if "lang_select" not in st.session_state:
    st.session_state.lang_select = "中文"
# 字体大小持久化保存，如果已存在则保持原值
if "font_size" not in st.session_state:
    st.session_state.font_size = "中号"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "默认白天"
if "fullscreen_mode" not in st.session_state:
    st.session_state.fullscreen_mode = False
if "auto_speak" not in st.session_state:
    st.session_state.auto_speak = False
if "story_likes" not in st.session_state:
    st.session_state.story_likes = app_data.get("story_likes", [])
if "user_profiles" not in app_data:
    app_data["user_profiles"] = {}

# ========================== 全局样式 ==========================
def set_style():
    font_map = {"小号":"14px","中号":"17px","大号":"20px"}
    fs = font_map[st.session_state.font_size]
    theme = st.session_state.theme_mode

    if theme == "默认白天":
        bg = f"background-image: url(data:image/jpg;base64,{bg1}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,249,250,0.92) 100%)"
        btn_bg = "linear-gradient(135deg, #8471f5 0%, #6352e5 100%)"
        text_color = "#222"
        card_shadow = "0 8px 32px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06)"
        card_hover_shadow = "0 12px 40px rgba(0,0,0,0.15), 0 4px 12px rgba(0,0,0,0.08)"

    elif theme == "夜间模式":
        bg = f"background-image: url(data:image/jpg;base64,{bg2}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(30,33,48,0.95) 0%, rgba(22,25,36,0.98) 100%)"
        btn_bg = "linear-gradient(135deg, #5b4cdb 0%, #4a3bcb 100%)"
        text_color = "#f0f0f0"
        card_shadow = "0 8px 32px rgba(0,0,0,0.3), 0 2px 8px rgba(0,0,0,0.2)"
        card_hover_shadow = "0 12px 40px rgba(0,0,0,0.4), 0 4px 12px rgba(0,0,0,0.3)"

    elif theme == "护眼绿色":
        bg = f"background-image: url(data:image/jpg;base64,{bg3}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(240,250,245,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #4CAF50 0%, #3d9a40 100%)"
        text_color = "#222"
        card_shadow = "0 8px 32px rgba(76,175,80,0.15), 0 2px 8px rgba(76,175,80,0.08)"
        card_hover_shadow = "0 12px 40px rgba(76,175,80,0.2), 0 4px 12px rgba(76,175,80,0.12)"

    elif theme == "暖黄温柔":
        bg = f"background-image: url(data:image/jpg;base64,{bg4}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(255,248,235,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #ffb74d 0%, #ffa726 100%)"
        text_color = "#222"
        card_shadow = "0 8px 32px rgba(255,183,77,0.15), 0 2px 8px rgba(255,183,77,0.08)"
        card_hover_shadow = "0 12px 40px rgba(255,183,77,0.2), 0 4px 12px rgba(255,183,77,0.12)"

    else:
        bg = f"background-image: url(data:image/jpg;base64,{bg1}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,249,250,0.92) 100%)"
        btn_bg = "linear-gradient(135deg, #8471f5 0%, #6352e5 100%)"
        text_color = "#222"
        card_shadow = "0 8px 32px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06)"
        card_hover_shadow = "0 12px 40px rgba(0,0,0,0.15), 0 4px 12px rgba(0,0,0,0.08)"

    st.markdown(f"""
    <style>
    .stApp {{ 
        {bg} 
        color:{text_color};
        transition: all 0.5s ease-in-out;
        min-height: 100vh;
    }}
    
    .story-card {{ 
        background:{card_bg}; 
        border-radius:20px; 
        padding:28px; 
        font-size:{fs}; 
        line-height:1.8; 
        box-shadow:{card_shadow};
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(255,255,255,0.5);
        margin: 16px 0;
    }}
    
    .story-card:hover {{
        box-shadow:{card_hover_shadow};
        transform: translateY(-4px);
    }}
    
    .story-card h1, .story-card h2, .story-card h3, .story-card h4, .story-card h5, .story-card h6 {{ 
        font-size:{fs}; 
        margin-top:1.5em; 
        margin-bottom:0.5em; 
        transition: color 0.3s ease;
    }}
    
    .story-card p {{ 
        font-size:{fs}; 
        margin-bottom:1em; 
        transition: color 0.3s ease;
    }}
    
    .story-card ul, .story-card ol {{ font-size:{fs}; }}
    
    .story-card li {{ font-size:{fs}; }}
    
    .story-card * {{ font-size:{fs} !important; }}
    
    .stButton>button {{ 
        background:{btn_bg}; 
        color:white; 
        border-radius:12px; 
        border:none; 
        padding:8px 16px; 
        font-weight:500;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }}
    
    .stButton>button:active {{
        transform: translateY(0);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }}
    
    .stRadio > div {{ gap:12px; }}
    
    .stColumns > div {{ padding:4px; }}
    
    .stTextArea>div>textarea {{
        border-radius:12px;
        border: 1px solid rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }}
    
    .stTextArea>div>textarea:focus {{
        border-color: #8471f5;
        box-shadow: 0 0 0 3px rgba(132,113,245,0.1);
    }}
    
    .stDownloadButton>button {{
        background:{btn_bg};
        color:white;
        border-radius:12px;
        border:none;
        padding:8px 16px;
        font-weight:500;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    
    .stDownloadButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }}
    
    .stSuccess {{
        background: linear-gradient(135deg, rgba(76,175,80,0.1) 0%, rgba(76,175,80,0.05) 100%);
        border-left: 4px solid #4CAF50;
        border-radius: 0 12px 12px 0;
        transition: all 0.4s ease;
    }}
    
    section.main {{
        transition: opacity 0.4s ease, transform 0.4s ease;
    }}
    
    @media (max-width: 768px) {{
        .story-card {{
            padding: 20px !important;
            border-radius: 16px !important;
            margin: 12px 0 !important;
        }}
        
        .stButton>button {{
            min-height: 44px !important;
            padding: 12px 20px !important;
            font-size: 16px !important;
            border-radius: 14px !important;
        }}
        
        .stDownloadButton>button {{
            min-height: 44px !important;
            padding: 12px 20px !important;
            font-size: 16px !important;
            border-radius: 14px !important;
        }}
        
        .stRadio > div {{
            flex-wrap: wrap !important;
            gap: 8px !important;
        }}
        
        .stRadio > div > label {{
            min-width: calc(50% - 4px) !important;
            text-align: center !important;
        }}
        
        .stTextInput>div>input,
        .stTextArea>div>textarea {{
            min-height: 44px !important;
            font-size: 16px !important;
        }}
        
        .stSelectbox>div>div {{
            min-height: 44px !important;
        }}
        
        /* 响应式表格样式 */
        .responsive-table {{
            overflow-x: auto !important;
            border-radius: 12px !important;
            box-shadow: {card_shadow} !important;
        }}
        
        .responsive-table table {{
            width: 100% !important;
            border-collapse: collapse !important;
            font-size: 14px !important;
        }}
        
        .responsive-table th,
        .responsive-table td {{
            padding: 12px 8px !important;
            text-align: left !important;
            border-bottom: 1px solid rgba(0,0,0,0.1) !important;
            white-space: nowrap !important;
        }}
        
        .responsive-table th {{
            background: rgba(132,113,245,0.1) !important;
            font-weight: 600 !important;
        }}
        
        .responsive-table tr:hover {{
            background: rgba(132,113,245,0.05) !important;
        }}
    }}
    
    @media (max-width: 480px) {{
        .story-card {{
            padding: 16px !important;
            border-radius: 12px !important;
            margin: 8px 0 !important;
        }}
        
        .story-card * {{
            font-size: 16px !important;
        }}
        
        .stButton>button {{
            min-height: 48px !important;
            padding: 14px 24px !important;
            font-size: 16px !important;
            border-radius: 16px !important;
        }}
        
        .stDownloadButton>button {{
            min-height: 48px !important;
            padding: 14px 24px !important;
            font-size: 16px !important;
            border-radius: 16px !important;
        }}
        
        .stRadio > div {{
            flex-direction: column !important;
            gap: 6px !important;
        }}
        
        .stRadio > div > label {{
            min-width: 100% !important;
            min-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}
        
        .stTextInput>div>input,
        .stTextArea>div>textarea {{
            min-height: 48px !important;
            font-size: 16px !important;
            padding: 12px !important;
        }}
        
        .stSelectbox>div>div {{
            min-height: 48px !important;
        }}
        
        .stSlider>div>div {{
            padding: 0 !important;
        }}
    }}
    
    </style>
    """, unsafe_allow_html=True)

# ========================== 工具函数 ==========================
def encrypt_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()

# 阅读时长
def get_read_time(text):
    if text is None:
        return "⏱ 阅读时长：0 分钟"
    cnt = len(text)
    speed = 300
    mins = max(1, cnt // speed)
    return f"⏱ 阅读时长：{mins} 分钟"

# 字数统计
def get_word_count(text):
    if text is None:
        return 0
    return len(text)

# 收藏
def add_to_favorite(story):
    for item in st.session_state.favorite_stories:
        if item["time"] == story["time"]:
            return False
    story["score"] = 0
    st.session_state.favorite_stories.append(story)
    app_data["favorite_stories"] = st.session_state.favorite_stories
    save_data(app_data)
    return True

def remove_from_favorite(story):
    for idx, item in enumerate(st.session_state.favorite_stories):
        if item["time"] == story["time"]:
            del st.session_state.favorite_stories[idx]
            app_data["favorite_stories"] = st.session_state.favorite_stories
            save_data(app_data)
            return True
    return False

# 点赞功能
def like_story(story):
    key = story["time"]
    if key not in st.session_state.story_likes:
        st.session_state.story_likes.append(key)
        app_data["story_likes"] = st.session_state.story_likes
        save_data(app_data)
        return True
    return False

def unlike_story(story):
    key = story["time"]
    if key in st.session_state.story_likes:
        st.session_state.story_likes.remove(key)
        app_data["story_likes"] = st.session_state.story_likes
        save_data(app_data)
        return True
    return False

# 朗读 / 停止
def speak_text(text, lang="zh-CN"):
    text = text.replace("`", "'")
    js = f"""
    <script>
    function speak() {{
        window.speechSynthesis.cancel();
        let t = `{text}`;
        let u = new SpeechSynthesisUtterance(t);
        u.lang = '{lang}';
        u.rate = 0.95;
        speechSynthesis.speak(u);
    }}
    speak();
    </script>
    """
    st.components.v1.html(js, height=0)

def stop_speak():
    st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)

# 复制到剪贴板
def copy_text_btn(text):
    js = f"""
    <script>
    function copy() {{
        let t = `{text.replace("`", "'")}`;
        navigator.clipboard.writeText(t);
        alert("已复制到剪贴板");
    }}
    copy();
    </script>
    """
    st.components.v1.html(js, height=0)

# 导出PDF
def export_pdf(title, content):
    if not REPORTLAB_AVAILABLE:
        st.warning("⚠️ PDF 导出功能不可用，请安装 reportlab 库")
        return None
        
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, title)
    c.setFont("Helvetica", 12)
    y_pos = height - 80
    line_height = 20
    for line in content.split("\n"):
        if y_pos < 50:
            c.showPage()
            y_pos = height - 50
        c.drawString(50, y_pos, line)
        y_pos -= line_height
    c.save()
    buffer.seek(0)
    return buffer

# 导出全部
def export_all_stories():
    all_text = ""
    for s in st.session_state.story_history:
        all_text += f"【{s['style']}】{s['keyword']} {s['time']}\n{s['content']}\n{'='*40}\n\n"
    return all_text

# 今日生成计数
def get_today_count():
    today = datetime.now().strftime("%Y-%m-%d")
    daily_count = app_data.get("daily_count", {})
    return daily_count.get(today, 0)

def add_today_count():
    today = datetime.now().strftime("%Y-%m-%d")
    if "daily_count" not in app_data:
        app_data["daily_count"] = {}
    app_data["daily_count"][today] = app_data["daily_count"].get(today, 0) + 1
    save_data(app_data)

# 随机主题风格
random_themes = ["森林冒险","校园青春","追梦少年","古风江湖","太空探索","小动物故事","亲情温暖","成长励志"]
random_styles = ["童话","励志","校园","古风","科幻"]
emotion_list = ["治愈温柔","欢乐轻松","伤感文艺","冒险刺激","悬疑神秘"]
mood_list = ["开心快乐", "安静治愈", "疲惫放松", "难过安慰", "迷茫鼓励"]

# ========================== 侧边栏设置 ==========================
def sidebar_setting():
    with st.sidebar:
        st.title("⚙️ 全局设置")
        selected_theme = st.radio("🎨 主题皮肤", ["默认白天","夜间模式","护眼绿色","暖黄温柔"], key="sidebar_theme")
        if selected_theme != st.session_state.theme_mode:
            st.session_state.theme_mode = selected_theme
            st.rerun()

        st.session_state.lang_select = st.radio("🌐 故事语言", ["中文", "英文", "中英双语"], key="sidebar_lang")
        # 确保字体大小在 session state 中持久化
        if "font_size" not in st.session_state:
            st.session_state.font_size = "中号"
        selected_font = st.radio("🔤 字体大小", ["小号","中号","大号"], index=["小号","中号","大号"].index(st.session_state.font_size), key="sidebar_font")
        if selected_font != st.session_state.font_size:
            st.session_state.font_size = selected_font
            st.rerun()
        st.divider()
        st.session_state.auto_speak = st.checkbox(" 生成后自动朗读", value=st.session_state.auto_speak)
        st.divider()
        st.info(f"📅 今日已生成：{get_today_count()} 篇")
        st.info("👋 未登录可游客模式临时使用")

# ========================== 登录注册 / 游客模式 ==========================
def user_login():
    with st.sidebar:
        st.title("🔐 用户中心")
        if not st.session_state.logged_in:
            tab1, tab2 = st.tabs(["登录", "注册"])
            with tab1:
                un = st.text_input("用户名", key="login_user")
                pw = st.text_input("密码", type="password", key="login_pwd")
                if st.button("登录"):
                    if un in st.session_state.users and st.session_state.users[un] == encrypt_password(pw):
                        st.session_state.logged_in = True
                        st.session_state.username = un
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
            with tab2:
                un_new = st.text_input("设置用户名", key="reg_user")
                pw_new = st.text_input("设置密码", type="password", key="reg_pwd")
                pw_conf = st.text_input("确认密码", type="password", key="reg_conf")
                if st.button("注册"):
                    if un_new in st.session_state.users:
                        st.error("用户名已存在")
                    elif pw_new != pw_conf:
                        st.error("两次密码不一致")
                    else:
                        st.session_state.users[un_new] = encrypt_password(pw_new)
                        app_data["users"] = st.session_state.users
                        save_data(app_data)
                        st.success("注册成功，请登录")
            st.divider()
            st.info("✅ 无需登录也可直接创作（游客模式）")
        else:
            st.success(f"已登录：{st.session_state.username}")

# ========================== 生成故事公共函数 ==========================
def generate_story(keyword, style, emotion, word_num, length_opt, is_visitor=False):
    """使用 LangChain 创意写作助手生成故事"""
    lang = st.session_state.lang_select
    content = None
    
    try:
        # 使用 LangChain 生成故事
        content = generate_story_with_langchain(
            keyword=keyword,
            style=style,
            emotion=emotion,
            mood=st.session_state.get('mood', '开心快乐'),
            language=lang,
            word_count=word_num
        )
    except Exception as e:
        content = None
    
    # 如果 LangChain 失败或返回 None，回退到原始方法
    if content is None:
        if lang == "中文":
            prompt = f"请先给故事起一个优美的标题，再写一篇{style}风格、{emotion}氛围的完整小故事，主题：{keyword}，**严格控制在{word_num}字左右，误差不超过 50 字**，段落清晰，情节完整。"
        elif lang == "英文":
            prompt = f"Give a beautiful title first, then write a complete {style} short story with {emotion} atmosphere, theme: '{keyword}', **strictly about {word_num} words**, pure English no Chinese."
        else:
            prompt = f"先起精美标题，写一篇{style}风格{emotion}氛围**严格{word_num}字左右**中文故事，再做标准中英双语对照。"
        
        res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content": prompt}])
        content = res.choices[0].message.content

    story_item = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "keyword": keyword,
        "style": style,
        "emotion": emotion,
        "content": content,
        "score": 0
    }
    st.session_state.current_story = story_item
    if not is_visitor:
        st.session_state.story_history.append(story_item)
        app_data["story_history"] = st.session_state.story_history
        add_today_count()
        save_data(app_data)
    if st.session_state.auto_speak:
        speak_text(content)
    st.rerun()

# ========================== 1.创作故事页 ==========================
def create_story_page():
    st.title("📖 AI 故事创作平台")
    st.markdown("<p style='color:#666;margin-bottom:20px;'>✨ 一键生成治愈、励志、古风、科幻等精美短篇故事</p>", unsafe_allow_html=True)
    is_visitor = not st.session_state.logged_in
    if is_visitor:
        st.warning("👋 游客模式：可正常创作，不保存历史、收藏记录")

    if "temp_keyword" not in st.session_state:
        st.session_state.temp_keyword = ""
    if "temp_style" not in st.session_state:
        st.session_state.temp_style = "童话"
    if "temp_emotion" not in st.session_state:
        st.session_state.temp_emotion = "治愈温柔"

    mood = st.radio("🧧 心情模式", mood_list, horizontal=True)
    keyword = st.text_input("✨ 输入故事主题", value=st.session_state.temp_keyword, placeholder="例如：星光、成长、晚风")
    
    st.markdown(" 故事风格（可多选）")
    style_options = ["童话", "励志", "校园", "古风", "科幻"]
    
    if "selected_styles" not in st.session_state:
        st.session_state.selected_styles = []
    
    style_cols = st.columns(5)
    for i, opt in enumerate(style_options):
        with style_cols[i]:
            is_selected = opt in st.session_state.selected_styles
            if st.checkbox(opt, value=is_selected, key=f"style_chk_{i}"):
                if opt not in st.session_state.selected_styles:
                    st.session_state.selected_styles.append(opt)
            else:
                if opt in st.session_state.selected_styles:
                    st.session_state.selected_styles.remove(opt)
    
    style_selected = ",".join(st.session_state.selected_styles) if st.session_state.selected_styles else st.session_state.temp_style
    
    if "custom_style_input" not in st.session_state:
        st.session_state.custom_style_input = ""
    
    custom_emotion = st.text_input("✏️ 自定义风格", value=st.session_state.custom_style_input, placeholder="输入自定义风格，如：赛博朋克、武侠", key="custom_style_input")
    style = custom_emotion.strip() if custom_emotion.strip() else style_selected
    
    st.markdown(" 故事情绪氛围（可多选）")
    
    if "selected_emotions" not in st.session_state:
        st.session_state.selected_emotions = []
    
    emotion_cols = st.columns(5)
    for i, opt in enumerate(emotion_list):
        with emotion_cols[i]:
            is_selected = opt in st.session_state.selected_emotions
            if st.checkbox(opt, value=is_selected, key=f"emotion_chk_{i}"):
                if opt not in st.session_state.selected_emotions:
                    st.session_state.selected_emotions.append(opt)
            else:
                if opt in st.session_state.selected_emotions:
                    st.session_state.selected_emotions.remove(opt)
    
    emotion_selected = ",".join(st.session_state.selected_emotions) if st.session_state.selected_emotions else st.session_state.temp_emotion
    
    if "custom_emotion_input" not in st.session_state:
        st.session_state.custom_emotion_input = ""
    
    custom_emotion = st.text_input("️ 自定义情绪氛围", value=st.session_state.custom_emotion_input, placeholder="输入自定义氛围，如：温馨浪漫、紧张压抑", key="custom_emotion_input")
    emotion = custom_emotion.strip() if custom_emotion.strip() else emotion_selected

    col_len1, col_len2 = st.columns(2)
    with col_len1:
        length_opt = st.select_slider("📏 快速字数", ["短篇150字", "中篇350字", "长篇600字"])
    with col_len2:
        # 设置自定义字数默认值为350
        if "custom_num" not in st.session_state:
            st.session_state.custom_num = 350
        custom_num = st.number_input("✏️ 自定义字数", min_value=50, max_value=2000, value=st.session_state.custom_num, step=50, key="custom_num_input")
        st.session_state.custom_num = custom_num

    st.session_state.temp_keyword = keyword
    st.session_state.temp_style = style
    st.session_state.temp_emotion = emotion

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✨ 开始创作") and keyword:
            generate_story(keyword, style, emotion, custom_num, length_opt, is_visitor)
    with col2:
        if st.button("🔁 同主题重新生成") and keyword:
            generate_story(keyword, style, emotion, custom_num, length_opt, is_visitor)
    with col3:
        if st.button("🎲 随机生成故事"):
            import random
            rk = random.choice(random_themes)
            rs = random.choice(random_styles)
            re = random.choice(emotion_list)
            generate_story(rk, rs, re, 350, "中篇350字", is_visitor)
    with col4:
        if st.button("💖 按心情生成") and keyword:
            generate_story(keyword, style, mood, custom_num, length_opt, is_visitor)

    if st.session_state.current_story:
        s = st.session_state.current_story
        word_total = get_word_count(s["content"])
        st.success(f"✅ 故事生成完成｜{get_read_time(s['content'])}｜总字数：{word_total}")

        if st.session_state.editing_story:
            edited_content = st.text_area("编辑故事内容", s["content"], height=400)
            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button("💾 保存修改"):
                    s["content"] = edited_content
                    st.session_state.editing_story = False
                    st.success("✓ 修改已保存")
                    st.rerun()
            with ec2:
                if st.button("❌ 取消编辑"):
                    st.session_state.editing_story = False
                    st.rerun()
        else:
            st.markdown(f"<div class='story-card'>{s['content']}</div>", unsafe_allow_html=True)

            c1,c2,c3,c4,c5,c6,c7,c8,c9 = st.columns(9)
            with c1:
                if not is_visitor and st.button("⭐ 收藏"):
                    ok = add_to_favorite(s)
                    st.success("已收藏" if ok else "已收藏过")
            with c2:
                liked = s["time"] in st.session_state.story_likes
                if st.button("👍 点赞" if not liked else "❤️ 已点赞"):
                    if not liked:
                        like_story(s)
                    else:
                        unlike_story(s)
                    st.rerun()
            with c3:
                if s["content"]:
                    st.download_button(" TXT 下载", s["content"], file_name=f"{s['keyword']}.txt")
                else:
                    st.download_button("📥 TXT 下载", "", file_name=f"{s['keyword']}.txt")
            with c4:
                if s["content"]:
                    pdf_buf = export_pdf(s['keyword'], s['content'])
                    st.download_button("📄 导出 PDF", pdf_buf, file_name=f"{s['keyword']}_故事.pdf", mime="application/pdf")
                else:
                    st.download_button("📄 导出 PDF", "", file_name=f"{s['keyword']}_故事.pdf", mime="application/pdf")
            with c5:
                if st.button("🔊 朗读"):
                    speak_text(s["content"])
            with c6:
                if st.button("⏹️ 停止"):
                    stop_speak()
            with c7:
                if st.button("✏️ 编辑故事"):
                    st.session_state.editing_story = True
                    st.rerun()
            with c8:
                if st.button("🧘 全屏阅读"):
                    st.session_state.fullscreen_mode = True
                    st.rerun()
            with c9:
                if st.button("🔄 清空"):
                    st.session_state.confirm_clear_story = True
            
            # 清空当前故事确认对话框
            if st.session_state.get('confirm_clear_story', False):
                st.warning("⚠️ 确定要清空当前故事吗？此操作不可恢复！")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ 确认清空", key="confirm_clear_story_btn"):
                        st.session_state.current_story = None
                        st.session_state.confirm_clear_story = False
                        st.rerun()
                with col_cancel:
                    if st.button("❌ 取消", key="cancel_clear_story_btn"):
                        st.session_state.confirm_clear_story = False
                        st.rerun()

        st.divider()
        # 调整按钮布局，让它们居中对称显示
        action_cols = st.columns([1, 2, 2, 1])  # 两侧留空，中间两个按钮
        
        with action_cols[1]:
            if st.button("📉 故事缩写精简", use_container_width=True):
                prompt = f"把下面故事精简缩写成100字左右，保留主线剧情：\n{s['content']}"
                res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.markdown(f"<div class='story-card'>【缩写版本】\n{res.choices[0].message.content}</div>", unsafe_allow_html=True)
        
        with action_cols[2]:
            if st.button("✍️ 续写当前故事", use_container_width=True):
                prompt = f"接续故事继续写150字，保持风格：{s['style']}，氛围：{s['emotion']}：\n{s['content']}"
                res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                s["content"] += "\n\n【续写】\n" + res.choices[0].message.content
                st.rerun()

# ========================== 全屏阅读模式 ==========================
if st.session_state.fullscreen_mode and st.session_state.current_story:
    s = st.session_state.current_story
    st.title("🧘 沉浸式阅读")
    st.markdown(f"<div class='story-card' style='padding:40px; line-height:2; font-size:18px'>{s['content']}</div>", unsafe_allow_html=True)
    if st.button("🔙 返回编辑页"):
        st.session_state.fullscreen_mode = False
        st.rerun()
    st.stop()

# ========================== 2.创作历史 ==========================
def history_page():
    st.title("📚 我的创作历史")
    if not st.session_state.logged_in:
        st.warning("⚠️ 请先登录查看个人历史记录")
        return

    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        s_txt = st.text_input("🔍 搜索关键词", key="history_search", placeholder="输入关键词后按回车搜索")
    with search_col2:
        st.write("")
        st.write("")
        search_btn = st.button("搜索", key="history_search_btn")
    
    filter_style = st.selectbox("📂 按风格筛选", ["全部","童话","励志","校园","古风","科幻"], key="history_style_filter")
    st.download_button("📤 一键导出全部", export_all_stories(), file_name="我的所有故事.txt")

    list_data = []
    search_term = s_txt.strip() if s_txt else ""
    
    if search_term:
        for story in st.session_state.story_history:
            if search_term in story["keyword"] or search_term in story["content"]:
                list_data.append(story)
    else:
        list_data = st.session_state.story_history.copy()
    
    if filter_style != "全部":
        list_data = [x for x in list_data if x["style"] == filter_style]

    if not list_data:
        st.info("暂无匹配故事")
        return

    for idx, item in enumerate(reversed(list_data)):
        with st.expander(f"【{item['style']}】{item['keyword']} | {item['time']}"):
            st.write(item["content"])
            st.caption(f"{get_read_time(item['content'])}｜{get_word_count(item['content'])}字｜⭐评分：{item.get('score',0)}")
            score = st.slider("⭐ 故事评分", 0,5, item.get("score",0), key=f"score_{idx}")
            if item.get("score",0) != score:
                item["score"] = score
                app_data["story_history"] = st.session_state.story_history
                save_data(app_data)
                st.rerun()

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1:
                if st.button("⭐ 收藏", key=f"h_fav_{idx}"):
                    add_to_favorite(item)
                    st.rerun()
            with c2:
                liked = item["time"] in st.session_state.story_likes
                if st.button("👍 点赞" if not liked else "❤️ 已点赞", key=f"h_like_{idx}"):
                    like_story(item) if not liked else unlike_story(item)
                    st.rerun()
            with c3:
                if st.button("🔊 朗读", key=f"h_read_{idx}"):
                    speak_text(item["content"])
            with c4:
                if st.button("⏹️ 停止", key=f"h_stop_{idx}"):
                    stop_speak()
            with c5:
                if st.button("📋 复制", key=f"h_copy_{idx}"):
                    copy_text_btn(item["content"])
            with c6:
                if st.button("✍️ 故事续写", key=f"h_next_{idx}"):
                    prompt = f"接续下面的故事继续往下写，情节连贯，风格保持{item['style']}，氛围{item['emotion']}，续写150字左右：\n{item['content']}"
                    res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    new_cont = item["content"] + "\n\n【续写内容】\n" + res.choices[0].message.content
                    item["content"] = new_cont
                    app_data["story_history"] = st.session_state.story_history
                    save_data(app_data)
                    st.rerun()

# ========================== 3.收藏夹 ==========================
def favorite_page():
    st.title("❤️ 我的收藏夹")
    if not st.session_state.logged_in:
        st.warning("⚠️ 请先登录查看收藏")
        return

    if st.button("🗑️ 一键清空全部收藏"):
        st.session_state.favorite_stories = []
        app_data["favorite_stories"] = []
        save_data(app_data)
        st.success("✅ 已清空所有收藏")
        st.rerun()

    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        s_txt = st.text_input("🔍 搜索收藏故事", key="fav_search", placeholder="输入关键词后按回车或点击搜索")
    with search_col2:
        st.write("")
        st.write("")
        search_btn = st.button("搜索", key="fav_search_btn")
    
    filter_style = st.selectbox("📂 按风格筛选", ["全部","童话","励志","校园","古风","科幻"], key="fav_style_filter")

    list_data = st.session_state.favorite_stories.copy()
    if filter_style != "全部":
        list_data = [x for x in list_data if x["style"] == filter_style]
    
    search_term = s_txt.strip() if s_txt else ""
    if search_term:
        list_data = [x for x in list_data if search_term in x["keyword"] or search_term in x["content"]]

    if not list_data:
        st.info("暂无收藏")
        return

    for idx, item in enumerate(list_data):
        with st.expander(f"【{item['style']}】{item['keyword']} | {item['time']}"):
            st.write(item["content"])
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                if st.button("🗑️ 取消收藏", key=f"f_del_{idx}"):
                    remove_from_favorite(item)
                    st.rerun()
            with c2:
                if st.button("🔊 朗读", key=f"f_read_{idx}"):
                    speak_text(item["content"])
            with c3:
                if st.button("⏹️ 停止", key=f"f_stop_{idx}"):
                    stop_speak()
            with c4:
                if st.button("📋 复制", key=f"f_copy_{idx}"):
                    copy_text_btn(item["content"])

# ========================== 4.个人中心 ==========================
def mine_page():
    st.title("👤 个人中心")
    if not st.session_state.logged_in:
        st.warning("⚠️ 请先登录")
        return

    user = st.session_state.username
    profiles = app_data.get("user_profiles", {})
    
    # 获取用户头像（支持上传本地图片）
    avatar = profiles.get(user, {}).get("avatar", "")
    avatar_type = profiles.get(user, {}).get("avatar_type", "")
    
    # 显示当前头像
    if avatar and isinstance(avatar, str) and avatar.startswith('iVBORw0'):
        st.markdown("""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{}" style="max-width: 100px; width: 100%; height: auto; max-height: 100px; border-radius: 50%; object-fit: cover;" />
        </div>
        """.format(avatar), unsafe_allow_html=True)
    elif avatar and isinstance(avatar, str) and avatar.startswith('/9j/'):
        st.markdown("""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/jpeg;base64,{}" style="max-width: 100px; width: 100%; height: auto; max-height: 100px; border-radius: 50%; object-fit: cover;" />
        </div>
        """.format(avatar), unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <div style="width:100px; height:100px; background:#8471f5; border-radius:50%; display:grid; place-items:center; color:white; font-size:40px;">
            """+user[0].upper()+"""
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"<h2 style='text-align:center;'>{user}</h2>", unsafe_allow_html=True)

    # 修改头像功能
    st.divider()
    st.subheader("🖼️ 修改头像")
    
    # 使用 session state 防止无限 rerun
    if "avatar_uploaded" not in st.session_state:
        st.session_state.avatar_uploaded = False
    
    # 上传本地图片作为头像
    uploaded_file = st.file_uploader("上传本地图片作为头像", type=["jpg", "jpeg", "png", "gif"], key="avatar_uploader")
    if uploaded_file is not None and not st.session_state.avatar_uploaded:
        # 读取图片内容
        image_data = uploaded_file.read()
        original_size = len(image_data) / 1024
        
        # 压缩图片
        compressed_data = compress_image(image_data, max_size_kb=100, quality=80, max_dimension=512)
        compressed_size = len(compressed_data) / 1024
        
        # 转换为 base64 字符串保存
        image_base64 = base64.b64encode(compressed_data).decode()
        
        if user not in profiles:
            profiles[user] = {}
        profiles[user]["avatar"] = image_base64
        profiles[user]["avatar_type"] = "image/jpeg"  # 压缩后统一为 JPEG 格式
        app_data["user_profiles"] = profiles
        save_data(app_data)
        st.session_state.avatar_uploaded = True
        
        # 显示压缩信息
        if original_size > compressed_size:
            saved_percent = ((original_size - compressed_size) / original_size * 100)
            st.success(f"头像上传成功！图片已压缩：{original_size:.1f}KB → {compressed_size:.1f}KB（节省 {saved_percent:.1f}%）")
        else:
            st.success(f"头像上传成功！图片大小：{compressed_size:.1f}KB")
        
        st.rerun()
    
    # 重置上传状态
    if st.session_state.avatar_uploaded and not uploaded_file:
        st.session_state.avatar_uploaded = False
    
    # 清除头像（恢复默认）
    if avatar and st.button("🔄 恢复默认头像"):
        if user in profiles:
            profiles[user].pop("avatar", None)
            profiles[user].pop("avatar_type", None)
            app_data["user_profiles"] = profiles
            save_data(app_data)
            st.success("已恢复默认头像")
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 创作总数", len(st.session_state.story_history))
    with col2:
        st.metric("⭐ 收藏总数", len(st.session_state.favorite_stories))
    with col3:
        st.metric("👍 获赞总数", len(st.session_state.story_likes))

    st.divider()

    st.subheader("✍️ 个人签名")
    sign = profiles.get(user, {}).get("signature", "这个用户很懒，什么都没留下~")
    st.info(sign)

    new_sign = st.text_input("修改签名")
    if st.button("保存签名"):
        if user not in profiles:
            profiles[user] = {}
        profiles[user]["signature"] = new_sign
        app_data["user_profiles"] = profiles
        save_data(app_data)
        st.success("保存成功")
        st.rerun()

    st.divider()
    st.subheader("🏆 我的高分故事")
    ranked = sorted([s for s in st.session_state.story_history if s.get("score",0)>0], key=lambda x:x["score"], reverse=True)
    if ranked:
        for i, s in enumerate(ranked[:5]):
            st.write(f"第{i+1}名 ⭐{s['score']}｜{s['keyword']}")
    else:
        st.info("暂无评分")

    st.divider()
    st.subheader("🔐 修改密码")
    old = st.text_input("原密码", type="password")
    new1 = st.text_input("新密码", type="password")
    new2 = st.text_input("确认密码", type="password")
    if st.button("保存修改"):
        if st.session_state.users[user] != encrypt_password(old):
            st.error("原密码错误")
        elif new1 != new2:
            st.error("两次不一致")
        else:
            st.session_state.users[user] = encrypt_password(new1)
            app_data["users"] = st.session_state.users
            save_data(app_data)
            st.success("修改成功")

    st.divider()
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🧹 清空创作历史"):
            st.session_state.confirm_clear_history = True
    
    # 清空创作历史确认对话框
    if st.session_state.get('confirm_clear_history', False):
        st.warning("⚠️ 确定要清空所有创作历史吗？此操作不可恢复！")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("✅ 确认清空", key="confirm_clear_btn"):
                st.session_state.story_history = []
                app_data["story_history"] = []
                save_data(app_data)
                st.session_state.confirm_clear_history = False
                st.success("已清空创作历史")
                st.rerun()
        with col_cancel:
            if st.button("❌ 取消", key="cancel_clear_btn"):
                st.session_state.confirm_clear_history = False
                st.rerun()
    
    with c2:
        if st.button("🚪 退出登录"):
            st.session_state.logged_in = False
            st.rerun()

# ========================== 5.灵感库 ==========================
def quote_page():
    st.title("💡 故事灵感库")
    st.markdown("<p style='color:#666;margin-bottom:20px;'>✨ 提供故事灵感、写作技巧、经典桥段参考</p>", unsafe_allow_html=True)
    
    type_sel = st.radio("选择类型", [
        "故事灵感",
        "写作技巧",
        "经典桥段",
        "角色设定",
        "情节反转"
    ])
    
    if st.button("✨ 获取灵感"):
        prompts = {
            "故事灵感": "生成10个独特的故事灵感，包含奇幻、科幻、现实等不同类型，每个灵感用一句话描述，激发创作欲望。",
            "写作技巧": "分享10条实用的写作技巧，涵盖情节构建、人物塑造、氛围营造等方面，每条技巧简洁明了。",
            "经典桥段": "列举10个经典的故事桥段模板，如英雄之旅、复仇故事、成长故事等，每个桥段说明其结构特点。",
            "角色设定": "生成10个有趣的角色设定，包含角色的外貌、性格、背景故事，适合不同类型的故事。",
            "情节反转": "提供10个出人意料的情节反转点子，每个反转简洁有力，适合加入故事中增加戏剧性。"
        }
        prompt = prompts[type_sel]
        res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
        st.markdown(f"<div class='story-card'>{res.choices[0].message.content}</div>", unsafe_allow_html=True)

# ========================== 6.【全新升级】管理员后台 ==========================

def admin_page():
    global app_data  # 核心修复：声明使用全局app_data
    st.title("🛡️ 超级管理员后台")
    admin_acc = "admin"
    admin_pwd = "admin123"

    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.is_admin:
        u = st.text_input("管理员账号")
        p = st.text_input("管理员密码", type="password")
        if st.button("登录后台"):
            if u == admin_acc and p == admin_pwd:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("账号密码错误")
        return

    st.success("✅ 管理员已登录，欢迎使用管理功能")

    # 顶部数据看板
    st.subheader("📊 全站数据总览")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("注册用户数", len(st.session_state.users))
    with col2:
        st.metric("全站故事数", len(st.session_state.story_history))
    with col3:
        st.metric("收藏总数", len(st.session_state.favorite_stories))
    with col4:
        st.metric("点赞总数", len(st.session_state.story_likes))
    with col5:
        st.metric("今日创作", get_today_count())

    st.divider()
    
    # LangChain 使用统计
    st.subheader(" LangChain 创意写作助手监控")
    
    if "usage_stats" not in st.session_state:
        st.session_state.usage_stats = {
            "total_tokens": 0,
            "total_cost": 0,
            "story_count": 0
        }
    
    col_usage1, col_usage2, col_usage3 = st.columns(3)
    with col_usage1:
        st.metric(
            label="📝 生成故事数",
            value=st.session_state.usage_stats.get("story_count", 0),
            delta="累计"
        )
    with col_usage2:
        st.metric(
            label="💾 Token 消耗",
            value=st.session_state.usage_stats.get("total_tokens", 0),
            delta=f"约{st.session_state.usage_stats.get('total_tokens', 0) / 1000:.2f}K"
        )
    with col_usage3:
        st.metric(
            label="💰 预估成本",
            value=f"${st.session_state.usage_stats.get('total_cost', 0):.4f}",
            delta="USD"
        )
    
    # LangSmith 监控状态
    st.subheader("📡 LangSmith 监控状态")
    langchain_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false") == "true"
    if langchain_enabled:
        st.success("✅ LangSmith 追踪已启用")
        st.info(f"项目名称：{os.getenv('LANGCHAIN_PROJECT', 'story-creator')}")
        st.markdown("[查看 LangSmith 监控面板](https://smith.langchain.com)")
    else:
        st.warning("⚠️ LangSmith 追踪未启用")
        st.markdown("""
        **启用方法**：
        1. 在 `.env` 文件中添加：
           - `LANGCHAIN_TRACING_V2=true`
           - `LANGCHAIN_API_KEY=your_api_key`
        2. 重启应用即可
        """)
    
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["👥 用户管理", "📖 故事管理", "📥 数据导出", "🗑️ 危险操作"])

    # ========== 标签1：用户管理 ==========
    with tab1:
        st.subheader("全部注册用户")
        user_list = list(st.session_state.users.keys())
        if not user_list:
            st.info("暂无注册用户")
        else:
            # 响应式用户列表 - 在小屏幕上使用卡片式布局
            for username in user_list:
                # 使用响应式列布局
                col_user, col_action = st.columns([1, 1], gap="small")
                with col_user:
                    st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.9); border-radius: 12px; padding: 12px 16px; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 8px;'>
                        <span style='font-size: 16px; font-weight: 500;'>👤 {username}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with col_action:
                    st.markdown("""
                    <div style='display: flex; align-items: center; justify-content: center; height: 100%;'>
                    """, unsafe_allow_html=True)
                    if st.button("删除", key=f"del_user_{username}", use_container_width=True):
                        st.session_state.confirm_delete_user = username
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # 删除用户确认对话框
            if st.session_state.get('confirm_delete_user', None):
                delete_user = st.session_state.confirm_delete_user
                st.warning(f"⚠️ 确定要删除用户「{delete_user}」吗？此操作不可恢复！")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ 确认删除", key="confirm_del_user_btn"):
                        del st.session_state.users[delete_user]
                        if delete_user in app_data["user_profiles"]:
                            del app_data["user_profiles"][delete_user]
                        app_data["users"] = st.session_state.users
                        save_data(app_data)
                        st.session_state.confirm_delete_user = None
                        st.success(f"已删除用户：{delete_user}")
                        st.rerun()
                with col_cancel:
                    if st.button("❌ 取消", key="cancel_del_user_btn"):
                        st.session_state.confirm_delete_user = None
                        st.rerun()

    # ========== 标签2：故事管理 ==========
    with tab2:
        st.subheader("全部故事管理（可删除违规内容）")
        search_txt = st.text_input("🔍 搜索故事关键词")
        all_stories = st.session_state.story_history.copy()
        if search_txt:
            all_stories = [s for s in all_stories if search_txt in s["keyword"] or search_txt in s["content"]]

        if not all_stories:
            st.info("暂无故事")
        else:
            # 显示故事统计
            st.info(f"共找到 {len(all_stories)} 个故事")
            
            for idx, story in enumerate(reversed(all_stories)):
                # 使用卡片式布局显示故事
                with st.container():
                    st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.9); border-radius: 12px; padding: 16px; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 12px;'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;'>
                            <div>
                                <span style='font-weight: 600; color: #8471f5;'>【{story['style']}】</span>
                                <span style='font-size: 16px; font-weight: 500; margin-left: 8px;'>{story['keyword']}</span>
                                <span style='font-size: 12px; color: #999; margin-left: 12px;'>{story['time']}</span>
                            </div>
                        </div>
                        <p style='font-size: 14px; line-height: 1.6; color: #555; margin-bottom: 12px;'>
                            {story['content'][:100]}{'...' if len(story['content']) > 100 else ''}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 删除按钮 - 使用响应式布局
                    if st.button(f"🗑️ 删除故事「{story['keyword']}」", key=f"del_story_{idx}", use_container_width=True):
                        # 将故事信息保存到 session state 以便确认
                        st.session_state.confirm_delete_story = {
                            "idx": idx,
                            "story": story
                        }
            
            # 删除故事确认对话框
            if st.session_state.get('confirm_delete_story', None):
                story_data = st.session_state.confirm_delete_story["story"]
                st.warning(f"⚠️ 确定要删除故事「{story_data['keyword']}」吗？此操作不可恢复！")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ 确认删除", key="confirm_del_story_btn"):
                        st.session_state.story_history.remove(story_data)
                        app_data["story_history"] = st.session_state.story_history
                        save_data(app_data)
                        st.session_state.confirm_delete_story = None
                        st.success("已删除")
                        st.rerun()
                with col_cancel:
                    if st.button("❌ 取消", key="cancel_del_story_btn"):
                        st.session_state.confirm_delete_story = None
                        st.rerun()

    # ========== 标签3：数据导出 ==========
    with tab3:
        st.subheader("一键导出全站数据")
        export_all = export_all_stories()
        st.download_button("📤 导出所有故事 TXT", export_all, file_name="全站所有故事.txt")
        st.download_button("📤 导出用户数据 JSON", json.dumps(app_data, ensure_ascii=False, indent=2), file_name="user_data_backup.json")

    # ========== 标签4：危险清空 ==========
    with tab4:
        st.warning("⚠️ 以下操作不可恢复，请谨慎！")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚠️ 清空所有故事、收藏、点赞"):
                st.session_state.story_history = []
                st.session_state.favorite_stories = []
                st.session_state.story_likes = []
                app_data["story_history"] = []
                app_data["favorite_stories"] = []
                app_data["story_likes"] = []
                save_data(app_data)
                st.success("已清空")
                st.rerun()
        with col2:
            if st.button("🚨 清空全站所有数据（含用户）"):
                st.session_state.users = {}
                st.session_state.story_history = []
                st.session_state.favorite_stories = []
                st.session_state.story_likes = []
                app_data = init_empty_data()
                save_data(app_data)
                st.success("全站数据已重置")
                st.rerun()

    st.divider()
    if st.button("🚪 退出管理员模式"):
        st.session_state.is_admin = False
        st.rerun()

# ========================== 主入口 ==========================
sidebar_setting()
set_style()
user_login()

tabs = st.tabs([
    "📖 创作故事",
    "📚 创作历史",
    "❤️ 收藏夹",
    "👤 个人中心",
    "💡 灵感库",
    "🛡️ 管理员后台"
])

with tabs[0]: create_story_page()
with tabs[1]: history_page()
with tabs[2]: favorite_page()
with tabs[3]: mine_page()
with tabs[4]: quote_page()
with tabs[5]: admin_page()