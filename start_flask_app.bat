@echo off

REM AIGC创意平台 - Flask应用启动脚本

REM 检查是否已安装Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python环境。请先安装Python并添加到系统环境变量。
    pause
    exit /b 1
)

REM 安装项目依赖
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败。请检查网络连接或requirements.txt文件。
    pause
    exit /b 1
)

REM 提示用户输入ComfyUI路径（如果尚未配置）
set /p COMFYUI_PATH="请输入ComfyUI安装路径（直接回车使用已有配置）: "

REM 如果用户提供了新的ComfyUI路径，更新配置文件
if not "%COMFYUI_PATH%" == "" (
    echo 更新ComfyUI配置...
    python -c "import json, os; config_path = os.path.join('configs', 'config.json'); with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f); config['comfyui']['path'] = '%COMFYUI_PATH%'; with open(config_path, 'w', encoding='utf-8') as f: json.dump(config, f, ensure_ascii=False, indent=2)"
    echo ComfyUI配置已更新。
)

REM 启动Flask应用
cd scripts
echo 正在启动AIGC创意平台...
echo 请等待服务器启动完成，然后在浏览器中访问 http://localhost:5000
echo.
echo 注意：请保持此窗口打开，关闭窗口将停止服务器。
echo.

python app_flask.py

REM 如果应用程序意外退出，显示错误信息
if %errorlevel% neq 0 (
    echo.
echo 错误: 应用程序启动失败。
pause
)

cd ..