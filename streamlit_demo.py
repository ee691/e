import streamlit as st
import base64
from openai import OpenAI

# ---------------------- 配置区 ----------------------
# 直接把密钥写在这里（只在作业演示用，发布前记得删除）
API_KEY = "你的DeepSeek密钥"
BASE_URL = "https://api.deepseek.com/v1"
MODEL_NAME = "deepseek-chat"

# ---------------------- 图片处理 ----------------------
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg1 = get_base64("4.jpg")

# ---------------------- 页面样式 ----------------------
st.markdown(f"""
<style>
.stApp {{ 
    background-image: url(data:image/jpg;base64,{bg1}); 
    background-size: cover; 
    background-position: center;
    background-attachment: fixed;
}}
.story-card {{ 
    background: rgba(255,255,255,0.9); 
    border-radius: 15px; 
    padding: 20px; 
    margin: 15px 0;
    line-height: 1.8;
}}
</style>
""", unsafe_allow_html=True)

# ---------------------- 核心功能 ----------------------
st.title("📖 AI 故事创作平台")
st.markdown("<p style='color:#666;'>✨ 一键生成治愈儿童故事</p>", unsafe_allow_html=True)

# 用户输入
keyword = st.text_input("输入故事主题（例如：星光、成长、晚风）")
word_count = st.number_input("字数", min_value=50, max_value=1000, value=300)

if st.button("✨ 生成故事") and keyword:
    with st.spinner("正在创作中..."):
        try:
            # 初始化客户端
            client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            
            # 调用模型
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": f"你是专业儿童故事作家，写一篇{word_count}字左右、温暖治愈的故事，主题是：{keyword}"},
                    {"role": "user", "content": keyword}
                ]
            )
            story = response.choices[0].message.content
            
            # 显示结果
            st.success("✅ 故事生成完成！")
            st.markdown(f"<div class='story-card'>{story}</div>", unsafe_allow_html=True)
            
            # 下载按钮
            st.download_button("📥 下载TXT", story, file_name=f"{keyword}_故事.txt")
            
        except Exception as e:
            st.error(f"生成失败：{str(e)}")