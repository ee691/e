import streamlit as st
import requests
import base64
import io
from datetime import datetime

# 云端兼容处理PDF库
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except:
    REPORTLAB_AVAILABLE = False

# ===================== 后端接口地址 =====================
BACKEND_URL = "http://127.0.0.1:10000"

# 图片转base64
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

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

# ===================== 初始化所有会话状态（原版全部） =====================
if "login_mode" not in st.session_state:
    st.session_state.login_mode = "游客模式"
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
if "selected_styles" not in st.session_state:
    st.session_state.selected_styles = ["童话"]
if "selected_emotions" not in st.session_state:
    st.session_state.selected_emotions = ["治愈温柔"]
if "style_check" not in st.session_state:
    st.session_state.style_check = {"童话":True,"励志":False,"校园":False,"古风":False,"科幻":False}
if "emotion_check" not in st.session_state:
    st.session_state.emotion_check = {"治愈温柔":True,"欢乐轻松":False,"伤感文艺":False,"冒险刺激":False,"悬疑神秘":False}
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
        text_color = "#f0f0"
    elif theme == "护眼绿色":
        bg = f"background-image: url(data:image/jpg;base64,{bg3}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(240,250,245,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #4CAF50 0%, #3d9a40 100%)"
        text_color = "#222"
    else:
        bg = f"background-image: url(data:image/jpg;base64,{bg4}) !important; background-size:cover !important; background-position:center !important; background-attachment:fixed !important;"
        card_bg = "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(255,248,235,0.93) 100%)"
        btn_bg = "linear-gradient(135deg, #ffb74d 0%, #ffa726 0%)"
        text_color = "#222"

    st.markdown(f"""
    <style>
    .stApp {{ {bg}; color:{text_color}; transition: all 0.5s ease-in-out; min-height: 100vh; }}
    .story-card {{ background:{card_bg}; border-radius:20px; padding:28px; font-size:{fs}; line-height:1.8; margin: 16px 0; }}
    .stButton>button {{ background:{btn_bg}; color:white; border-radius:12px; border:none; padding:8px 16px; }}
    </style>
    """, unsafe_allow_html=True)

# ===================== 顶部导航栏（原版原样） =====================
def top_nav():
    nav_list = ["创作故事","创作历史","收藏夹","个人中心","灵感库","管理员后台"]
    cols = st.columns(len(nav_list))
    for idx,name in enumerate(nav_list):
        with cols[idx]:
            if st.button(name,key=f"nav_{name}",use_container_width=True):
                st.session_state.nav_tab = name
                st.rerun()
    st.divider()

# ===================== 修复接口中文编码请求 =====================
def generate_story(keyword, style, emotion, word_num, mood, language):
    try:
        import json
        headers = {"Content-Type":"application/json;charset=utf-8"}
        data = {
            "keyword":keyword,
            "style":style,
            "emotion":emotion,
            "mood":mood,
            "language":language,
            "word_count":word_num
        }
        res = requests.post(
            f"{BACKEND_URL}/generate_story",
            headers=headers,
            data=json.dumps(data,ensure_ascii=False).encode("utf-8")
        )
        res_data = res.json()
        st.session_state.current_story = {"keyword":keyword,"content":res_data["content"]}
        if st.session_state.auto_speak:
            speak_text(res_data["content"])
        st.rerun()
    except Exception as e:
        st.error(f"请求后端失败：{e}")

# ===================== 侧边栏【完整原版：登录模式切换+全局设置】 =====================
def sidebar_setting():
    with st.sidebar:
        st.title("⚙️ 全局设置")
        # 1. 登录/游客模式切换（你要的这个）
        st.session_state.login_mode = st.radio("🔐 登录模式",["游客模式","账号登录"])
        if st.session_state.login_mode == "账号登录":
            un = st.text_input("用户名")
            pwd = st.text_input("密码",type="password")
            c1,c2 = st.columns(2)
            with c1:
                if st.button("登录"):
                    if un and pwd:
                        st.session_state.logged_in = True
                        st.session_state.username = un
                        st.success("登录成功")
                        st.rerun()
                    else:
                        st.warning("请填写账号密码")
            with c2:
                if st.button("注册"):
                    st.info("前往注册页面")
        else:
            st.info("当前：游客浏览模式")

        st.divider()
        # 2. 主题皮肤
        theme_sel = st.radio("🎨 主题皮肤",["默认白天","夜间模式","护眼绿色","暖黄温柔"])
        if theme_sel != st.session_state.theme_mode:
            st.session_state.theme_mode = theme_sel
            st.rerun()
        # 3. 故事语言
        st.session_state.lang_select = st.radio("🌐 故事语言",["中文","英文","中英双语"])
        # 4. 字体大小
        st.session_state.font_size = st.radio("🔤 字体大小",["小号","中号","大号"],index=1)
        # 5. 自动朗读
        st.session_state.auto_speak = st.checkbox("🔊 生成后自动朗读",value=False)

        # 登录后显示退出
        if st.session_state.logged_in:
            st.divider()
            st.write(f"👤 已登录：{st.session_state.username}")
            if st.button("退出登录"):
                st.session_state.logged_in = False
                st.session_state.login_mode = "游客模式"
                st.rerun()

# ===================== 主创作页面（完全原版界面） =====================
def main_page():
    top_nav()
    if st.session_state.nav_tab == "创作故事":
        st.title("📖 AI 故事创作平台")
        st.markdown("<p style='color:#666'>✨ 一键生成治愈、励志、古风、科幻等精美短篇故事</p>",unsafe_allow_html=True)
        if st.session_state.login_mode == "游客模式":
            st.info("👤 游客模式：可正常创作，不保存历史、收藏记录")

        mood_list = ["开心快乐","安静治愈","疲惫放松","难过安慰","迷茫鼓励"]
        mood = st.radio("🧧 心情模式",mood_list,horizontal=True)
        keyword = st.text_input("✨ 输入故事主题",placeholder="例如：星光、成长、晚风")

        # 故事风格多选
        st.markdown("### 🎨 故事风格（可多选）")
        style_opt = ["童话","励志","校园","古风","科幻"]
        cols_s = st.columns(5)
        for i,name in enumerate(style_opt):
            with cols_s[i]:
                ck = st.session_state.style_check[name]
                bgc = "#2ECC71" if ck else "#fff"
                bdc = "#2ECC71" if ck else "#ddd"
                tick = "✓" if ck else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:6px;">
                <div style="width:22px;height:22px;border:2px solid {bdc};background:{bgc};border-radius:4px;text-align:center;color:white;font-weight:bold;">{tick}</div>
                <span>{name}</span>
                </div>
                """,unsafe_allow_html=True)
                if st.button(" ",key=f"sty_{i}"):
                    st.session_state.style_check[name] = not ck
                    st.rerun()
        sel_style = [k for k,v in st.session_state.style_check.items() if v]
        style_str = "、".join(sel_style)
        custom_style = st.text_input("✏️ 自定义风格（可选）")
        if custom_style.strip():
            style_str = custom_style

        # 情绪氛围多选
        st.markdown("### 🎭 情绪氛围（可多选）")
        emo_opt = ["治愈温柔","欢乐轻松","伤感文艺","冒险刺激","悬疑神秘"]
        cols_e = st.columns(5)
        for i,name in enumerate(emo_opt):
            with cols_e[i]:
                ck = st.session_state.emotion_check[name]
                bgc = "#2ECC71" if ck else "#fff"
                bdc = "#2ECC71" if ck else "#ddd"
                tick = "✓" if ck else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:6px;">
                <div style="width:22px;height:22px;border:2px solid {bdc};background:{bgc};border-radius:4px;text-align:center;color:white;font-weight:bold;">{tick}</div>
                <span>{name}</span>
                </div>
                """,unsafe_allow_html=True)
                if st.button(" ",key=f"emo_{i}"):
                    st.session_state.emotion_check[name] = not ck
                    st.rerun()
        sel_emo = [k for k,v in st.session_state.emotion_check.items() if v]
        emo_str = "、".join(sel_emo)
        custom_emo = st.text_input("✏️ 自定义氛围（可选）")
        if custom_emo.strip():
            emo_str = custom_emo

        col1,col2 = st.columns(2)
        with col1:
            st.select_slider("📏 篇幅",["短篇150字","中篇350字","长篇600字"])
        with col2:
            word_num = st.number_input("✏️ 自定义字数",50,2000,350)

        b1,b2,b3 = st.columns(3)
        with b1:
            if st.button("✨ 开始创作") and keyword:
                generate_story(keyword,style_str,emo_str,word_num,mood,st.session_state.lang_select)
        with b2:
            if st.button("🔁 重新生成") and keyword:
                generate_story(keyword,style_str,emo_str,word_num,mood,st.session_state.lang_select)
        with b3:
            if st.button("🎲 随机故事"):
                import random
                ran_key = random.choice(["森林冒险","校园青春","追梦少年","古风江湖","太空探索"])
                generate_story(ran_key,style_str,emo_str,350,mood,st.session_state.lang_select)

        # 展示故事
        if st.session_state.current_story:
            art = st.session_state.current_story
            st.success(f"✅ 生成完成｜{get_read_time(art['content'])}｜字数：{get_word_count(art['content'])}")
            st.markdown(f"<div class='story-card'>{art['content']}</div>",unsafe_allow_html=True)
            d1,d2,d3,d4,d5,d6 = st.columns(6)
            with d1:st.download_button("📥 TXT",art["content"],f"{art['keyword']}.txt")
            with d2:
                if REPORTLAB_AVAILABLE:
                    st.download_button("📄 PDF",export_pdf(art["keyword"],art["content"]),f"{art['keyword']}.pdf")
                else:
                    st.button("📄 PDF",disabled=True)
            with d3:
                if st.button("🔊 朗读"):speak_text(art["content"])
            with d4:
                if st.button("⏹️ 停止"):stop_speak()
            with d5:
                if st.button("✏️ 编辑"):st.session_state.editing_story=True;st.rerun()
            with d6:
                if st.button("🔄 清空"):st.session_state.current_story=None;st.rerun()

    elif st.session_state.nav_tab == "创作历史":
        st.title("📚 创作历史")
        st.info("登录账号后即可查看所有创作记录")
    elif st.session_state.nav_tab == "收藏夹":
        st.title("❤️ 我的收藏")
        st.info("登录后使用收藏功能")
    elif st.session_state.nav_tab == "个人中心":
        st.title("👤 个人中心")
    elif st.session_state.nav_tab == "灵感库":
        st.title("💡 灵感素材库")
    elif st.session_state.nav_tab == "管理员后台":
        st.title("🔐 管理员后台")

# ===================== 程序入口 =====================
if __name__ == "__main__":
    set_style()
    sidebar_setting()
    main_page()