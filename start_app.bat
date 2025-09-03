@echo off

rem 简单的启动脚本 - 只包含核心功能


rem 创建虚拟环境
if not exist "env" (
    echo 创建Python虚拟环境...
    python -m venv env
)

rem 激活虚拟环境
echo 激活虚拟环境...
call env\Scripts\activate.bat

rem 安装依赖
echo 安装依赖包...
pip install -r requirements.txt

rem 启动应用
echo 启动AIGC演示应用...
streamlit run scripts\app.py

pause