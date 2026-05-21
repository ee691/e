import streamlit as st
from openai import OpenAI
from datetime import datetime
import hashlib
import os
import json
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import base64

# 安全导入 LangChain 相关（不报错）
LANGCHAIN_AVAILABLE = False
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain.memory import ConversationBufferMemory
    from langchain_core.tools import tool
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    LANGCHAIN_AVAILABLE = True
except:
    pass

# 安全导入 Pillow
PILLOW_AVAILABLE = False
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except:
    pass

# 本地图片转 base64
def get_base64(file):
    try:
        with open(file, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

# 图片压缩函数
def compress_image(image_data, max_size_kb=100, quality=80, max_dimension=512):
    if not PILLOW_AVAILABLE:
        return image_data
    try:
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        max_dim = max(width, height)
        if max_dim > max_dimension:
            ratio = max_dimension / max_dim
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        current_quality = quality
        while current_quality >= 10:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=current_quality)
            compressed_data = buffer.getvalue()
            if len(compressed_data) / 1024 <= max_size_kb:
                return compressed_data
            current_quality -= 10
        return image_data
    except:
        return image_data

# 4 个主题 4 张图（兼容无图片也不报错）
bg1 = get_base64("4.jpg")
bg2 = get_base64("1.1.jpeg")
bg3 = get_base64("1.2.png")
bg4 = get_base64("1.3.png")

# ========================== 配置文件路径（数据持久化） ==========================
DATA_FILE = "app_data.json"

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
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return init_empty_data()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app_data = load_data()

# ========================== 读取.env 密钥 ==========================
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "story-creator")

if not API_KEY:
    st.error("⚠️ 未读取到 API 密钥，请检查.env 文件")
    st.stop()

ai_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ========================== LangChain 安全封装 ==========================
if LANGCHAIN_AVAILABLE:
    @tool
    def count_words(text: str) -> int:
        return len(text.strip())
    @tool
    def check_word_limit(text: str, max_words: int) -> str:
        count = len(text.strip())
        if count > max_words:
            return f"超出字数限制！当前{count}字，要求{max_words}字"
        else:
            return f"字数合规！当前{count}字，要求{max_words}字"
    tools = [count_words, check_word_limit]
    story_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    def create_story_chain():
        llm = ChatOpenAI(temperature=0.7, model="deepseek-chat", base_url=BASE_URL, api_key=API_KEY)
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
        return AgentExecutor(agent=agent, tools=tools, memory=story_memory, verbose=False, max_iterations=2)

    def generate_story_with_langchain(keyword, style, emotion, mood, language, word_count):
        try:
            from langchain.callbacks import get_openai_callback
            agent = create_story_chain()
            with get_openai_callback() as cb:
                result = agent.invoke({
                    "keyword": keyword, "style": style, "emotion": emotion,
                    "mood": mood, "language": language, "word_count": word_count
                })
            if "usage_stats" not in st.session_state:
                st.session_state.usage_stats = {"total_tokens":0, "total_cost":0, "story_count":0}
            st.session_state.usage_stats["total_tokens"] += cb.total_tokens
            st.session_state.usage_stats["total_cost"] += cb.total_cost
            st.session_state.usage_stats["story_count"] += 1
            return result["output"]
        except:
            return None
else:
    def generate_story_with_langchain(*args, **kwargs):
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
        bg = f"background-image: url(data:image/jpg;base64,{bg1}) !important; background-size:cover !important;" if bg1 else ""
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,249,250,0.92) 100%)"
        btn_bg = "linear-gradient(135deg, #8471f5 0%, #6352e5 100%)"
        text_color = "#222"
    elif theme == "夜间模式":
        bg = f"background-image: url(data:image/jpg;base64,{bg2}) !important; background-size:cover !important;" if bg2 else ""
        card_bg = "linear-gradient(135deg, rgba(30,33,48,0.95) 0%, rgba(22,25,36,0.98) 100%)"
        btn_bg = "linear-gradient(135deg, #5b4cdb 0%, #4a3bcb 100%)"
        text_color = "#f0f0f0"
    elif theme == "护眼绿色":
        bg = f"background-image: url(data:image/jpg;base64,{bg3}) !important; background-size:cover !important;" if bg3 else ""
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(240,250,245,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #4CAF50 0%, #3d9a40 100%)"
        text_color = "#222"
    else:
        bg = f"background-image: url(data:image/jpg;base64,{bg4}) !important; background-size:cover !important;" if bg4 else ""
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(255,248,235,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #ffb74d 0%, #ffa726 100%)"
        text_color = "#222"

    st.markdown(f"""
    <style>
    .stApp {{ {bg}; color:{text_color}; transition: all 0.5s ease-in-out; min-height: 100vh; }}
    .story-card {{ background:{card_bg}; border-radius:20px; padding:28px; font-size:{fs}; line-height:1.8; margin:16px 0; }}
    .stButton>button, .stDownloadButton>button {{ background:{btn_bg}; color:white; border-radius:12px; border:none; padding:8px 16px; }}
    </style>
    """, unsafe_allow_html=True)

# ========================== 工具函数 ==========================
def encrypt_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()

def get_read_time(text):
    if not text: return "⏱ 阅读时长：0 分钟"
    return f"⏱ 阅读时长：{max(1, len(text)//300)} 分钟"

def get_word_count(text):
    return len(text) if text else 0

def add_to_favorite(story):
    for x in st.session_state.favorite_stories:
        if x["time"] == story["time"]: return False
    story["score"] = 0
    st.session_state.favorite_stories.append(story)
    app_data["favorite_stories"] = st.session_state.favorite_stories
    save_data(app_data)
    return True

def remove_from_favorite(story):
    for i,x in enumerate(st.session_state.favorite_stories):
        if x["time"] == story["time"]:
            del st.session_state.favorite_stories[i]
            app_data["favorite_stories"] = st.session_state.favorite_stories
            save_data(app_data)
            return True
    return False

def like_story(story):
    k = story["time"]
    if k not in st.session_state.story_likes:
        st.session_state.story_likes.append(k)
        app_data["story_likes"] = st.session_state.story_likes
        save_data(app_data)
        return True
    return False

def unlike_story(story):
    k = story["time"]
    if k in st.session_state.story_likes:
        st.session_state.story_likes.remove(k)
        app_data["story_likes"] = st.session_state.story_likes
        save_data(app_data)
        return True
    return False

def speak_text(text, lang="zh-CN"):
    text = text.replace("`", "'")
    st.components.v1.html(f"""
    <script>
    window.speechSynthesis.cancel();
    let u = new SpeechSynthesisUtterance(`{text}`);
    u.lang='{lang}'; u.rate=0.95;
    speechSynthesis.speak(u);
    </script>
    """, height=0)

def stop_speak():
    st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)

def copy_text_btn(text):
    text = text.replace("`", "'")
    st.components.v1.html(f"""
    <script>navigator.clipboard.writeText(`{text}`);alert("已复制");</script>
    """, height=0)

def export_pdf(title, content):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, h-50, title)
    c.setFont("Helvetica", 12)
    y = h-80
    for line in content.split("\n"):
        if y < 50: c.showPage(); y = h-50
        c.drawString(50, y, line)
        y -= 20
    c.save()
    buf.seek(0)
    return buf

def export_all_stories():
    t = ""
    for s in st.session_state.story_history:
        t += f"【{s['style']}】{s['keyword']} {s['time']}\n{s['content']}\n{'='*40}\n\n"
    return t

def get_today_count():
    today = datetime.now().strftime("%Y-%m-%d")
    return app_data.get("daily_count", {}).get(today, 0)

def add_today_count():
    today = datetime.now().strftime("%Y-%m-%d")
    if "daily_count" not in app_data: app_data["daily_count"] = {}
    app_data["daily_count"][today] = app_data["daily_count"].get(today, 0)+1
    save_data(app_data)

random_themes = ["森林冒险","校园青春","追梦少年","古风江湖","太空探索","小动物故事","亲情温暖","成长励志"]
random_styles = ["童话","励志","校园","古风","科幻"]
emotion_list = ["治愈温柔","欢乐轻松","伤感文艺","冒险刺激","悬疑神秘"]
mood_list = ["开心快乐", "安静治愈", "疲惫放松", "难过安慰", "迷茫鼓励"]

# ========================== 侧边栏 ==========================
def sidebar_setting():
    with st.sidebar:
        st.title("⚙️ 全局设置")
        t = st.radio("🎨 主题皮肤", ["默认白天","夜间模式","护眼绿色","暖黄温柔"])
        if t != st.session_state.theme_mode:
            st.session_state.theme_mode = t
            st.rerun()
        st.session_state.lang_select = st.radio("🌐 故事语言", ["中文", "英文", "中英双语"])
        f = st.radio("🔤 字体大小", ["小号","中号","大号"], index=["小号","中号","大号"].index(st.session_state.font_size))
        if f != st.session_state.font_size:
            st.session_state.font_size = f
            st.rerun()
        st.divider()
        st.session_state.auto_speak = st.checkbox("生成后自动朗读", value=st.session_state.auto_speak)
        st.divider()
        st.info(f"📅 今日已生成：{get_today_count()} 篇")
        st.info("👋 未登录可游客模式临时使用")

# ========================== 登录注册 ==========================
def user_login():
    with st.sidebar:
        st.title("🔐 用户中心")
        if not st.session_state.logged_in:
            t1, t2 = st.tabs(["登录", "注册"])
            with t1:
                un = st.text_input("用户名")
                pw = st.text_input("密码", type="password")
                if st.button("登录"):
                    if un in st.session_state.users and st.session_state.users[un] == encrypt_password(pw):
                        st.session_state.logged_in = True
                        st.session_state.username = un
                        st.rerun()
                    else:
                        st.error("账号或密码错误")
            with t2:
                nu = st.text_input("设置用户名")
                np = st.text_input("设置密码", type="password")
                nc = st.text_input("确认密码", type="password")
                if st.button("注册"):
                    if nu in st.session_state.users:
                        st.error("用户名已存在")
                    elif np != nc:
                        st.error("两次密码不一致")
                    else:
                        st.session_state.users[nu] = encrypt_password(np)
                        app_data["users"] = st.session_state.users
                        save_data(app_data)
                        st.success("注册成功")
            st.divider()
        else:
            st.success(f"已登录：{st.session_state.username}")

# ========================== 生成故事 ==========================
def generate_story(keyword, style, emotion, word_num, is_visitor=False):
    lang = st.session_state.lang_select
    mood = st.session_state.get("mood", "开心快乐")
    content = generate_story_with_langchain(keyword, style, emotion, mood, lang, word_num)
    if not content:
        if lang == "中文":
            prompt = f"标题+故事，{style}风格，{emotion}氛围，主题{keyword}，{word_num}字"
        elif lang == "英文":
            prompt = f"Write a {style} story {emotion} theme:{keyword} {word_num} words"
        else:
            prompt = f"标题+故事+中英对照，{style}，{emotion}，{keyword}，{word_num}字"
        res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
        content = res.choices[0].message.content
    item = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "keyword": keyword, "style": style, "emotion": emotion,
        "content": content, "score":0
    }
    st.session_state.current_story = item
    if not is_visitor:
        st.session_state.story_history.append(item)
        app_data["story_history"] = st.session_state.story_history
        add_today_count()
        save_data(app_data)
    if st.session_state.auto_speak:
        speak_text(content)
    st.rerun()

# ========================== 创作页面 ==========================
def create_story_page():
    st.title("📖 AI 故事创作平台")
    visitor = not st.session_state.logged_in
    if visitor:
        st.warning("👋 游客模式：可创作，不保存")
    mood = st.radio("🧧 心情模式", mood_list, horizontal=True)
    st.session_state.mood = mood
    kw = st.text_input("✨ 输入故事主题", placeholder="星光、成长、晚风")
    st.markdown("### 🎨 故事风格（可多选）")
    styles = ["童话","励志","校园","古风","科幻"]
    if "selected_styles" not in st.session_state:
        st.session_state.selected_styles = ["童话"]
    cols = st.columns(5)
    for i,s in enumerate(styles):
        with cols[i]:
            v = s in st.session_state.selected_styles
            if st.checkbox(s, value=v, key=f"sty{i}"):
                if s not in st.session_state.selected_styles:
                    st.session_state.selected_styles.append(s)
            else:
                if s in st.session_state.selected_styles:
                    st.session_state.selected_styles.remove(s)
    s_str = ",".join(st.session_state.selected_styles)
    cust_s = st.text_input("✏️ 自定义风格")
    if cust_s: s_str = cust_s
    st.markdown("### 🎭 情绪氛围（可多选）")
    if "selected_emotions" not in st.session_state:
        st.session_state.selected_emotions = ["治愈温柔"]
    e_cols = st.columns(5)
    for i,e in enumerate(emotion_list):
        with e_cols[i]:
            v = e in st.session_state.selected_emotions
            if st.checkbox(e, value=v, key=f"emo{i}"):
                if e not in st.session_state.selected_emotions:
                    st.session_state.selected_emotions.append(e)
            else:
                if e in st.session_state.selected_emotions:
                    st.session_state.selected_emotions.remove(e)
    e_str = ",".join(st.session_state.selected_emotions)
    cust_e = st.text_input("✏️ 自定义氛围")
    if cust_e: e_str = cust_e
    c1, c2 = st.columns(2)
    with c1:
        st.select_slider("📏 篇幅", ["短篇150字","中篇350字","长篇600字"])
    with c2:
        num = st.number_input("✏️ 自定义字数", 50,2000,350)
    b1,b2,b3,b4 = st.columns(4)
    with b1:
        if st.button("✨ 开始创作") and kw:
            generate_story(kw, s_str, e_str, num, visitor)
    with b2:
        if st.button("🔁 重新生成") and kw:
            generate_story(kw, s_str, e_str, num, visitor)
    with b3:
        if st.button("🎲 随机故事"):
            import random
            generate_story(random.choice(random_themes), random.choice(styles), random.choice(emotion_list), 350, visitor)
    with b4:
        if st.button("💖 按心情生成") and kw:
            generate_story(kw, s_str, mood, num, visitor)
    if st.session_state.current_story:
        s = st.session_state.current_story
        st.success(f"✅ 生成完成｜{get_read_time(s['content'])}｜字数：{len(s['content'])}")
        if st.session_state.editing_story:
            txt = st.text_area("编辑", s['content'], height=400)
            if st.button("💾 保存"):
                s['content'] = txt
                st.session_state.editing_story=False
                st.rerun()
        else:
            st.markdown(f"<div class='story-card'>{s['content']}</div>", unsafe_allow_html=True)
            cc = st.columns(9)
            with cc[0]:
                if not visitor and st.button("⭐ 收藏"): add_to_favorite(s);st.rerun()
            with cc[1]:
                liked = s['time'] in st.session_state.story_likes
                if st.button("👍 点赞" if not liked else "❤️ 已赞"):
                    like_story(s) if not liked else unlike_story(s);st.rerun()
            with cc[2]: st.download_button("📥 TXT", s['content'], f"{s['keyword']}.txt")
            with cc[3]: st.download_button("📄 PDF", export_pdf(s['keyword'],s['content']), f"{s['keyword']}.pdf")
            with cc[4]:
                if st.button("🔊 朗读"): speak_text(s['content'])
            with cc[5]:
                if st.button("⏹️ 停止"): stop_speak()
            with cc[6]:
                if st.button("✏️ 编辑"): st.session_state.editing_story=True;st.rerun()
            with cc[7]:
                if st.button("🧘 全屏"): st.session_state.fullscreen_mode=True;st.rerun()
            with cc[8]:
                if st.button("🔄 清空"): st.session_state.current_story=None;st.rerun()
            ac = st.columns([1,2,2,1])
            with ac[1]:
                if st.button("📉 缩写", use_container_width=True):
                    res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"缩写100字：{s['content']}"}])
                    st.markdown(f"<div class='story-card'>{res.choices[0].message.content}</div>", unsafe_allow_html=True)
            with ac[2]:
                if st.button("✍️ 续写", use_container_width=True):
                    res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"续写150字：{s['content']}"}])
                    s['content'] += "\n\n【续写】\n"+res.choices[0].message.content
                    st.rerun()

# ========================== 全屏 ==========================
if st.session_state.fullscreen_mode and st.session_state.current_story:
    s = st.session_state.current_story
    st.title("🧘 沉浸式阅读")
    st.markdown(f"<div class='story-card' style='padding:40px;font-size:18px;line-height:2'>{s['content']}</div>", unsafe_allow_html=True)
    if st.button("🔙 返回"):
        st.session_state.fullscreen_mode=False
        st.rerun()
    st.stop()

# ========================== 历史 ==========================
def history_page():
    st.title("📚 创作历史")
    if not st.session_state.logged_in:
        st.warning("请登录")
        return
    src = st.text_input("🔍 搜索")
    filt = st.selectbox("风格筛选", ["全部"]+random_styles)
    st.download_button("导出全部", export_all_stories(), "全部故事.txt")
    arr = st.session_state.story_history
    if src:
        arr = [x for x in arr if src in x['keyword'] or src in x['content']]
    if filt!="全部":
        arr = [x for x in arr if x['style']==filt]
    for x in reversed(arr):
        with st.expander(f"【{x['style']}】{x['keyword']} | {x['time']}"):
            st.write(x['content'])
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1:
                if st.button("⭐ 收藏", key=f"hf{x['time']}"):
                    add_to_favorite(x);st.rerun()
            with c2:
                lk = x['time'] in st.session_state.story_likes
                if st.button("👍 已赞" if lk else "👍 点赞", key=f"hl{x['time']}"):
                    like_story(x) if not lk else unlike_story(x);st.rerun()
            with c3:
                if st.button("朗读", key=f"hr{x['time']}"): speak_text(x['content'])
            with c4:
                if st.button("停止", key=f"hs{x['time']}"): stop_speak()
            with c5:
                if st.button("复制", key=f"hc{x['time']}"): copy_text_btn(x['content'])
            with c6:
                if st.button("续写", key=f"hn{x['time']}"):
                    res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"续写150字：{x['content']}"}])
                    x['content'] += "\n\n续写：\n"+res.choices[0].message.content
                    app_data["story_history"] = st.session_state.story_history
                    save_data(app_data)
                    st.rerun()

# ========================== 收藏 ==========================
def favorite_page():
    st.title("❤️ 收藏夹")
    if not st.session_state.logged_in:
        st.warning("请登录")
        return
    if st.button("清空收藏"):
        st.session_state.favorite_stories=[]
        app_data["favorite_stories"]=[]
        save_data(app_data)
        st.rerun()
    for x in st.session_state.favorite_stories:
        with st.expander(f"【{x['style']}】{x['keyword']}"):
            st.write(x['content'])
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                if st.button("取消收藏", key=f"fd{x['time']}"):
                    remove_from_favorite(x);st.rerun()
            with c2:
                if st.button("朗读", key=f"fr{x['time']}"): speak_text(x['content'])
            with c3:
                if st.button("停止", key=f"fs{x['time']}"): stop_speak()
            with c4:
                if st.button("复制", key=f"fc{x['time']}"): copy_text_btn(x['content'])

# ========================== 个人中心 ==========================
def mine_page():
    st.title("👤 个人中心")
    if not st.session_state.logged_in:
        st.warning("请登录")
        return
    user = st.session_state.username
    pros = app_data.get("user_profiles", {})
    ava = pros.get(user, {}).get("avatar", "")
    if ava:
        st.markdown(f"""<div style='text-align:center'><img src="data:image/jpeg;base64,{ava}" style='width:100px;height:100px;border-radius:50%'></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='text-align:center'><div style='width:100px;height:100px;background:#8471f5;border-radius:50%;margin:auto;color:white;font-size:40px;line-height:100px'>{user[0].upper()}</div></div>""", unsafe_allow_html=True)
    up = st.file_uploader("修改头像", type=["png","jpg"])
    if up:
        data = up.read()
        data = compress_image(data)
        b64 = base64.b64encode(data).decode()
        if user not in pros: pros[user] = {}
        pros[user]["avatar"] = b64
        app_data["user_profiles"] = pros
        save_data(app_data)
        st.success("上传成功")
        st.rerun()
    st.metric("创作数", len(st.session_state.story_history))
    sign = pros.get(user, {}).get("signature", "暂无签名")
    st.info(f"签名：{sign}")
    ns = st.text_input("修改签名")
    if st.button("保存签名"):
        pros[user]["signature"] = ns
        app_data["user_profiles"] = pros
        save_data(app_data)
        st.rerun()
    if st.button("退出登录"):
        st.session_state.logged_in=False
        st.rerun()

# ========================== 灵感库 ==========================
def quote_page():
    st.title("💡 灵感库")
    t = st.radio("类型", ["故事灵感","写作技巧","经典桥段","角色设定","情节反转"])
    if st.button("✨ 获取灵感"):
        m = {"故事灵感":"10个故事灵感","写作技巧":"10条写作技巧","经典桥段":"10个经典桥段","角色设定":"10个角色设定","情节反转":"10个反转"}
        res = ai_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":m[t]}])
        st.markdown(f"<div class='story-card'>{res.choices[0].message.content}</div>", unsafe_allow_html=True)

# ========================== 管理员 ==========================
def admin_page():
    st.title("🛡️ 管理员后台")
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    if not st.session_state.is_admin:
        u = st.text_input("账号")
        p = st.text_input("密码", type="password")
        if st.button("登录"):
            if u=="admin" and p=="admin123":
                st.session_state.is_admin=True
                st.rerun()
            else:
                st.error("错误")
        return
    st.success("已登录")
    st.metric("用户", len(st.session_state.users))
    st.metric("故事", len(st.session_state.story_history))
    tab1, tab2 = st.tabs(["用户","故事"])
    with tab1:
        for u in st.session_state.users:
            st.write("👤", u)
            if st.button("删除", key=f"ad{u}"):
                del st.session_state.users[u]
                app_data["users"] = st.session_state.users
                save_data(app_data)
                st.rerun()
    with tab2:
        for s in reversed(st.session_state.story_history):
            st.write(f"【{s['style']}】{s['keyword']}")
            if st.button("删除", key=f"as{s['time']}"):
                st.session_state.story_history.remove(s)
                app_data["story_history"] = st.session_state.story_history
                save_data(app_data)
                st.rerun()
    if st.button("退出管理员"):
        st.session_state.is_admin=False
        st.rerun()

# ========================== 主程序 ==========================
sidebar_setting()
set_style()
user_login()

tabs = st.tabs(["📖 创作故事","📚 创作历史","❤️ 收藏夹","👤 个人中心","💡 灵感库","🛡️ 管理员后台"])
with tabs[0]: create_story_page()
with tabs[1]: history_page()
with tabs[2]: favorite_page()
with tabs[3]: mine_page()
with tabs[4]: quote_page()
with tabs[5]: admin_page()