@echo off

rem 激活虚拟环境
echo 激活虚拟环境...
call .venv\Scripts\activate.bat

rem 启动应用
echo 启动AIGC演示应用...
streamlit run scripts\app.py

pause