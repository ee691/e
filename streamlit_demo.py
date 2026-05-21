import streamlit as st
import requests
import base64
import io
from datetime import datetime

# 处理reportlab导入
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except:
    REPORTLAB_AVAILABLE = False

# ===================== 后端地址 =====================
BACKEND_URL = "http://127.0.0.1:10000"

# 本地图片转 base64
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

# 背景图
bg1 = get_base64("4.jpg")
bg2 = get_base64("1.1.jpeg")
bg3 = get_base64("1.2.png")
bg4 = get_base64("1.3.png")

# ===================== 工具函数 =====================
def get_read_time(text):
    if not text:
        return "⏱ 阅读时长：0 分钟"
    cnt = len(text)
    speed = 300
    mins = max(1, cnt // speed)
    return f"⏱ 阅读时长：{mins} 分钟"

def get_word_count(text):
    return len(text) if text else 0

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

def export_pdf(title, content):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, title)
    c.setFont("Helvetica", 12)
    y_pos = height - 80
    for line in content.split("\n"):
        if y_pos < 50:
            c.showPage()
            y_pos = height - 50
        c.drawString(50, y_pos, line)
        y_pos -= 20
    c.save()
    buffer.seek(0)
    return buffer

# ===================== 初始化会话（恢复所有状态） =====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
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
if "auto_speak" not in st.session_state:
    st.session_state.auto_speak = False
if "style_check" not in st.session_state:
    st.session_state.style_check = {"童话":True,"励志":False,"校园":False,"古风":False,"科幻":False}
if "emotion_check" not in st.session_state:
    st.session_state.emotion_check = {"治愈温柔":True,"欢乐轻松":False,"伤感文艺":False,"冒险刺激":False,"悬疑神秘":False}
# 新增：导航栏状态
if "nav_tab" not in st.session_state:
    st.session_state.nav_tab = "创作故事"

# ===================== 全局样式 =====================
def set_style():
    font_map = {"小号":"14px","中号":"17px","大号":"20px"}
    fs = font_map[st.session_state.font_size]
    theme = st.session_state.theme_mode

    if theme == "默认白天":
        bg = f"background-image: url(data:image/jpg;base64,{bg1}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,249,250,0.92) 100%)"
        btn_bg = "linear-gradient(135deg, #8471f5 0%, #6352e5 100%)"
        text_color = "#222"
    elif theme == "夜间模式":
        bg = f"background-image: url(data:image/jpg;base64,{bg2}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(30,33,48,0.95) 0%, rgba(22,25,36,0.98) 100%)"
        btn_bg = "linear-gradient(135deg, #5b4cdb 0%, #4a3bcb 100%)"
        text_color = "#f0f0f0"
    elif theme == "护眼绿色":
        bg = f"background-image: url(data:image/jpg;base64,{bg3}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(240,250,245,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #4CAF50 0%, #3d9a40 100%)"
        text_color = "#222"
    else:
        bg = f"background-image: url(data:image/jpg;base64,{bg4}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(255,248,235,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #ffb74d 0%, #ffa726 100%)"
        text_color = "#222"

    st.markdown(f"""
    <style>
    .stApp {{ {bg}; color:{text_color}; transition: all 0.5s ease-in-out; min-height: 100vh; }}
    .story-card {{ background:{card_bg}; border-radius:20px; padding:28px; font-size:{fs}; line-height:1.8; margin: 16px 0; }}
    .stButton>button {{ background:{btn_bg}; color:white; border-radius:12px; border:none; padding:8px 16px; }}
    </style>
    """, unsafe_allow_html=True)

# ===================== 顶部导航栏（还原你本地的样式） =====================
def top_nav():
    tabs = ["创作故事", "创作历史", "收藏夹", "个人中心", "灵感库", "管理员后台"]
    cols = st.columns(len(tabs))
    for i, tab in enumerate(tabs):
        with cols[i]:
            if st.button(tab, key=f"nav_{tab}", type="primary" if st.session_state.nav_tab == tab else "secondary"):
                st.session_state.nav_tab = tab
                st.rerun()
    st.divider()

# ===================== 修复：调用后端接口 =====================
def generate_story(keyword, style, emotion, word_num, mood, language):
    try:
        import json
        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        payload = {
            "keyword": keyword,
            "style": style,
            "emotion": emotion,
            "mood": mood,
            "language": language,
            "word_count": word_num
        }
        
        res = requests.post(
            f"{BACKEND_URL}/generate_story",
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8")
        )
        
        data = res.json()
        st.session_state.current_story = {
            "keyword": keyword,
            "content": data["content"]
        }
        
        if st.session_state.auto_speak:
            speak_text(data["content"])
            
        st.rerun()
    except Exception as e:
        st.error(f"连接后端失败：{str(e)}")

# ===================== 登录/注册页面 =====================
def login_page():
    st.title("📖 AI 故事创作平台")
    st.markdown("请先登录或注册")
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        if st.button("登录"):
            if username and password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("请输入用户名和密码")
    
    with tab2:
        new_user = st.text_input("设置用户名")
        new_pass = st.text_input("设置密码", type="password")
        confirm_pass = st.text_input("确认密码", type="password")
        if st.button("注册"):
            if new_pass != confirm_pass:
                st.error("两次密码不一致")
            elif new_user and new_pass:
                st.success("注册成功，请登录")
            else:
                st.error("请填写完整信息")

# ===================== 创作页面（修复多选乱码） =====================
def create_story_page():
    # 顶部导航栏
    top_nav()
    
    # 根据导航栏切换显示不同内容
    if st.session_state.nav_tab == "创作故事":
        st.title("📖 AI 故事创作平台")
        st.markdown("<p style='color:#666;margin-bottom:20px;'>✨ 一键生成治愈、励志、古风、科幻等精美短篇故事</p>", unsafe_allow_html=True)
        
        # 游客模式提示
        st.info("👤 游客模式：可正常创作，不保存历史、收藏记录")

        mood_list = ["开心快乐", "安静治愈", "疲惫放松", "难过安慰", "迷茫鼓励"]
        style_options = ["童话", "励志", "校园", "古风", "科幻"]
        emotion_options = ["治愈温柔", "欢乐轻松", "伤感文艺", "冒险刺激", "悬疑神秘"]

        mood = st.radio("🧧 心情模式", mood_list, horizontal=True)
        keyword = st.text_input("✨ 输入故事主题", placeholder="例如：星光、成长、晚风")

        # 修复后的故事风格多选
        st.markdown("### 🎨 故事风格（可多选）")
        cols_style = st.columns(5)
        for i, opt in enumerate(style_options):
            with cols_style[i]:
                checked = st.session_state.style_check[opt]
                bg_color = "#2ECC71" if checked else "#ffffff"
                border_color = "#2ECC71" if checked else "#ddd"
                tick = "✓" if checked else ""

                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                    <div style="width:24px;height:24px;border-radius:4px;border:2px solid {border_color};background:{bg_color};display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:16px;">
                        {tick}
                    </div>
                    <span style="font-size:15px;">{opt}</span>
                </div>
                """, unsafe_allow_html=True)

                if st.button(" ", key=f"style_toggle_{i}", help=opt):
                    st.session_state.style_check[opt] = not checked
                    st.rerun()

        selected_styles = [k for k, v in st.session_state.style_check.items() if v]
        style_final = "、".join(selected_styles)
        custom_style = st.text_input("✏️ 自定义风格（可选）", placeholder="如：赛博朋克、武侠")
        if custom_style.strip():
            style_final = custom_style

        # 修复后的情绪氛围多选
        st.markdown("### 🎭 情绪氛围（可多选）")
        cols_emo = st.columns(5)
        for i, opt in enumerate(emotion_options):
            with cols_emo[i]:
                checked = st.session_state.emotion_check[opt]
                bg_color = "#2ECC71" if checked else "#ffffff"
                border_color = "#2ECC71" if checked else "#ddd"
                tick = "✓" if checked else ""

                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                    <div style="width:24px;height:24px;border-radius:4px;border:2px solid {border_color};background:{bg_color};display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:16px;">
                        {tick}
                    </div>
                    <span style="font-size:15px;">{opt}</span>
                </div>
                """, unsafe_allow_html=True)

                if st.button(" ", key=f"emo_toggle_{i}", help=opt):
                    st.session_state.emotion_check[opt] = not checked
                    st.rerun()

        selected_emotions = [k for k, v in st.session_state.emotion_check.items() if v]
        emotion_final = "、".join(selected_emotions)
        custom_emotion = st.text_input("✏️ 自定义氛围（可选）", placeholder="如：温馨、紧张、浪漫")
        if custom_emotion.strip():
            emotion_final = custom_emotion

        col_len1, col_len2 = st.columns(2)
        with col_len1:
            st.select_slider("📏 篇幅", ["短篇150字", "中篇350字", "长篇600字"])
        with col_len2:
            custom_num = st.number_input("✏️ 自定义字数", 50, 2000, 350)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✨ 开始创作") and keyword:
                generate_story(keyword, style_final, emotion_final, custom_num, mood, st.session_state.lang_select)
        with col2:
            if st.button("🔁 重新生成") and keyword:
                generate_story(keyword, style_final, emotion_final, custom_num, mood, st.session_state.lang_select)
        with col3:
            if st.button("🎲 随机故事"):
                import random
                rand_key = random.choice(["森林冒险","校园青春","追梦少年","古风江湖","太空探索"])
                rand_style = random.choice(style_options)
                rand_emo = random.choice(emotion_options)
                generate_story(rand_key, rand_style, rand_emo, 350, mood, st.session_state.lang_select)

        if st.session_state.current_story:
            s = st.session_state.current_story
            st.success(f"✅ 生成完成｜{get_read_time(s['content'])}｜字数：{get_word_count(s['content'])}")
            st.markdown(f"<div class='story-card'>{s['content']}</div>", unsafe_allow_html=True)

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1: st.download_button("📥 TXT", s["content"], f"{s['keyword']}.txt")
            with c2:
                if REPORTLAB_AVAILABLE:
                    st.download_button("📄 PDF", export_pdf(s['keyword'], s['content']), f"{s['keyword']}.pdf")
                else:
                    st.button("📄 PDF（暂不可用）", disabled=True)
            with c3:
                if st.button("🔊 朗读"): speak_text(s["content"])
            with c4:
                if st.button("⏹️ 停止"): stop_speak()
            with c5:
                if st.button("✏️ 编辑"): st.session_state.editing_story = True; st.rerun()
            with c6:
                if st.button("🔄 清空"): st.session_state.current_story = None; st.rerun()
    
    elif st.session_state.nav_tab == "创作历史":
        st.title("📚 创作历史")
        st.info("💡 游客模式不保存创作历史，登录后可查看")
    
    elif st.session_state.nav_tab == "收藏夹":
        st.title("❤️ 我的收藏")
        st.info("💡 游客模式不保存收藏，登录后可使用")
    
    elif st.session_state.nav_tab == "个人中心":
        st.title("👤 个人中心")
        st.write(f"当前用户：{st.session_state.username}")
        st.write("功能开发中...")
    
    elif st.session_state.nav_tab == "灵感库":
        st.title("💡 灵感库")
        st.write("功能开发中，敬请期待...")
    
    elif st.session_state.nav_tab == "管理员后台":
        st.title("🔐 管理员后台")
        st.info("管理员功能开发中...")

# ===================== 侧边栏 =====================
def sidebar_setting():
    with st.sidebar:
        st.title("⚙️ 全局设置")
        selected_theme = st.radio("🎨 主题皮肤", ["默认白天","夜间模式","护眼绿色","暖黄温柔"], key="sidebar_theme")
        if selected_theme != st.session_state.theme_mode:
            st.session_state.theme_mode = selected_theme
            st.rerun()
        st.session_state.lang_select = st.radio("🌐 故事语言", ["中文", "英文", "中英双语"])
        st.session_state.font_size = st.radio("🔤 字体大小", ["小号","中号","大号"], index=["小号","中号","大号"].index(st.session_state.font_size))
        st.session_state.auto_speak = st.checkbox("🔊 生成后自动朗读", value=st.session_state.auto_speak)
        
        # 退出登录
        if st.session_state.logged_in:
            st.divider()
            st.write(f"👤 当前用户：{st.session_state.username}")
            if st.button("退出登录"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()

# ===================== 主入口 =====================
def main():
    set_style()
    sidebar_setting()
    if not st.session_state.logged_in:
        login_page()
    else:
        create_story_page()

if __name__ == "__main__":
    main()