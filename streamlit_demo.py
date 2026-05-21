import streamlit as st
import requests
import json

# ---------------------- 配置区 ----------------------
API_KEY = "你的DeepSeek密钥"
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"

# ---------------------- 页面设置 ----------------------
st.set_page_config(page_title="AI故事创作平台", layout="wide")
st.title("📖 AI 故事创作平台")
st.markdown("✨ 一键生成治愈、励志、古风等精美短篇故事")

# ---------------------- 用户输入 ----------------------
keyword = st.text_input("输入故事主题（例如：星光、成长、晚风）", placeholder="在这里输入你的故事主题...")
word_count = st.slider("选择故事字数", min_value=100, max_value=1000, value=300, step=50)

# ---------------------- 生成故事 ----------------------
if st.button("✨ 开始创作") and keyword:
    with st.spinner("正在为你编织故事中..."):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
            data = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": f"你是专业儿童故事作家，写一篇{word_count}字左右、温暖治愈的故事，主题是：{keyword}"},
                    {"role": "user", "content": keyword}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(BASE_URL, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            result = response.json()
            story = result["choices"][0]["message"]["content"]
            
            st.success("✅ 故事生成完成！")
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.9); padding:25px; border-radius:15px; margin:15px 0; line-height:1.8;">
                {story}
            </div>
            """, unsafe_allow_html=True)
            
            st.download_button("📥 下载故事TXT", story, file_name=f"{keyword}_故事.txt")
            
        except Exception as e:
            st.error(f"生成失败：{str(e)}")