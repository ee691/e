 AI智能故事创作平台
项目概述：
本项目基于LangChain框架开发，采用前后端分离架构设计，利用大语言模型实现智能故事自动生成功能。
前端使用Streamlit搭建可视化操作页面，后端通过LangServe封装调用大模型接口，全部功能已在本地完成部署调试，运行稳定流畅。

开发技术
- 开发语言：Python
- 后端技术：LangChain、LangServe、FastAPI
- 前端技术：Streamlit
- 数据存储：本地JSON文件
- 运行环境：本地电脑运行

项目结构
backend.py 后端服务文件
frontend.py  前端页面文件
requirements.txt 项目依赖
README.md  项目说明
streamlit_demo.py  完整可独立运行成品前端页面


 文件用途说明
1. streamlit_demo.py
完整整合版页面，自带登录注册、主题切换、故事生成、历史记录全部功能，**无需对接后端也能直接运行**，目前云端部署使用该文件。

2. frontend.py
标准前后端分离专用前端，需要搭配本地backend后端服务一起启动使用，用于课程前后端分离实训学习。

3. backend.py
后端核心服务，封装提示词模板与链式调用逻辑，本地运行前端时启用。

运行方式
 方式一：直接运行成品页面（最简单，云端部署使用）
streamlit run streamlit_demo.py

方式二：标准前后端分离本地运行
1. 安装依赖
pip install -r requirements.txt

2. 启动后端
uvicorn backend:app --port 8000

3. 启动正式前端
streamlit run frontend.py

 实现全部功能
1. 用户注册、登录、退出登录
2. 自定义故事主题、心情、创作风格
3. 一键生成AI短篇故事
4. 登录账号自动保存创作历史
5. 侧边栏界面主题美化设置
6. 多分类标签页布局设计
