@echo off

rem 启动AIGC演示应用的Web界面

rem 设置Python虚拟环境（如果有）
activate venv\Scripts\activate

rem 安装依赖
pip install -r requirements.txt

rem 启动Web应用
python scripts\app.py

pause