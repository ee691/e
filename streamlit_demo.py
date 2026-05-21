import streamlit as st
import base64
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# 背景图片
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg1 = get_base64("4.jpg")

# 页面样式
st.markdown(f"""
<style>
.stApp {{ background-image: url(data:image/jpg;base64,{bg1}); background-size:cover; }}
</style>
""", unsafe_allow_html=True)

st.title("📖 AI 故事创作平台")
keyword = st.text_input("输入故事主题")

if keyword and st.button("生成故事"):
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL")
    )
    res = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"user","content":f"写一个300字的儿童故事，主题：{keyword}"}]
    )
    st.write(res.choices[0].message.content)