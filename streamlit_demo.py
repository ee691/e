import streamlit as st
import base64
import requests
import json

# ---------------------- 配置区 ----------------------
API_KEY = "你的DeepSeek密钥"
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"

# ---------------------- 图片处理 ----------------------
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg1 = get_base64("4.jpg")
bg2 = get_base64("1.1.jpeg")
bg3 = get_base64("1.2.png")
bg4 = get_base64("1.3.png")

# ---------------------- 工具函数 ----------------------
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

# ---------------------- 会话状态初始化 ----------------------
if "current_story" not in st.session_state:
    st.session_state.current_story = None
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "默认白天"
if "auto_speak" not in st.session_state:
    st.session_state.auto_speak = False
if "style_check" not in st.session_state:
    st.session_state.style_check = {"童话":True,"励志":False,"校园":False,"古风":False,"科幻":False}
if "emotion_check" not in st.session_state:
    st.session_state.emotion_check = {"治愈温柔":True,"欢乐轻松":False,"伤感文艺":False,"冒险刺激":False,"悬疑神秘":False}

# ---------------------- 页面样式 ----------------------
def set_style():
    font_map = {"小号":"14px","中号":"17px","大号":"20px"}
    fs = font_map["中号"]
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

# ---------------------- 故事生成核心（修复中文编码） ----------------------
def generate_story(keyword, style, emotion, word_num, mood):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": f"你是专业儿童故事生成器，风格：{style}，情绪：{emotion}，心情：{mood}，字数控制在{word_num}字左右"},
            {"role": "user", "content": keyword}
        ],
        "temperature": 0.7
    }
    
    # 强制使用UTF-8编码发送请求，解决中文乱码问题
    response = requests.post(
        BASE_URL,
        headers=headers,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8")
    )
    response.raise_for_status()
    result = response.json()
    story = result["choices"][0]["message"]["content"]
    
    st.session_state.current_story = {"keyword": keyword, "content": story}
    if st.session_state.auto_speak:
        speak_text(story)
    st.rerun()

# ---------------------- 页面内容 ----------------------
def create_story_page():
    st.title("📖 AI 故事创作平台")
    st.markdown("<p style='color:#666;margin-bottom:20px;'>✨ 一键生成治愈、励志、古风、科幻等精美短篇故事</p>", unsafe_allow_html=True)
    mood_list = ["开心快乐", "安静治愈", "疲惫放松", "难过安慰", "迷茫鼓励"]
    style_options = ["童话", "励志", "校园", "古风", "科幻"]
    emotion_options = ["治愈温柔", "欢乐轻松", "伤感文艺", "冒险刺激", "悬疑神秘"]
    mood = st.radio("🧧 心情模式", mood_list, horizontal=True)
    keyword = st.text_input("✨ 输入故事主题", placeholder="例如：星光、成长、晚风")

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
                <div style="width:24px;height:24px;border-radius:4px;border:2px solid {border_color};background:{bg_color};display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:16px;">{tick}</div>
                <span style="font-size:15px;">{opt}</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button(" ", key=f"style_toggle_{i}"):
                st.session_state.style_check[opt] = not checked
                st.rerun()
    selected_styles = [k for k, v in st.session_state.style_check.items() if v]
    style_final = "、".join(selected_styles)
    custom_style = st.text_input("✏️ 自定义风格（可选）")
    if custom_style.strip():
        style_final = custom_style

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
                <div style="width:24px;height:24px;border-radius:4px;border:2px solid {border_color};background:{bg_color};display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:16px;">{tick}</div>
                <span style="font-size:15px;">{opt}</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button(" ", key=f"emo_toggle_{i}"):
                st.session_state.emotion_check[opt] = not checked
                st.rerun()
    selected_emotions = [k for k, v in st.session_state.emotion_check.items() if v]
    emotion_final = "、".join(selected_emotions)
    custom_emotion = st.text_input("✏️ 自定义氛围（可选）")
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
            generate_story(keyword, style_final, emotion_final, custom_num, mood)
    with col2:
        if st.button("🔁 重新生成") and keyword:
            generate_story(keyword, style_final, emotion_final, custom_num, mood)
    with col3:
        if st.button("🎲 随机故事"):
            import random
            rand_key = random.choice(["森林冒险","校园青春","追梦少年","古风江湖","太空探索"])
            rand_style = random.choice(style_options)
            rand_emo = random.choice(emotion_options)
            generate_story(rand_key, rand_style, rand_emo, 350, mood)

    if st.session_state.current_story:
        s = st.session_state.current_story
        st.success(f"✅ 生成完成｜{get_read_time(s['content'])}｜字数：{get_word_count(s['content'])}")
        st.markdown(f"<div class='story-card'>{s['content']}</div>", unsafe_allow_html=True)
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.download_button("📥 TXT", s["content"], f"{s['keyword']}.txt")
        with c2:
            if st.button("🔊 朗读"): speak_text(s["content"])
        with c3:
            if st.button("⏹️ 停止"): stop_speak()
        with c4:
            if st.button("✏️ 编辑"): st.session_state.editing_story = True; st.rerun()
        with c5:
            if st.button("🔄 清空"): st.session_state.current_story = None; st.rerun()

def sidebar_setting():
    with st.sidebar:
        st.title("⚙️ 全局设置")
        selected_theme = st.radio("🎨 主题皮肤", ["默认白天","夜间模式","护眼绿色","暖黄温柔"], key="sidebar_theme")
        if selected_theme != st.session_state.theme_mode:
            st.session_state.theme_mode = selected_theme
            st.rerun()
        st.session_state.auto_speak = st.checkbox("🔊 生成后自动朗读", value=st.session_state.auto_speak)

def main():
    set_style()
    sidebar_setting()
    create_story_page()

if __name__ == "__main__":
    main()