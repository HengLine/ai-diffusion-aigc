@echo off
chcp 65001 >nul

REM AIGC创意平台 - Flask应用启动脚本（优化版）

REM 检查是否已安装Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境。请先安装Python并添加到系统环境变量。
    pause
    exit /b 1
)

REM 创建并激活虚拟环境
if not exist "env" (
    echo 创建Python虚拟环境...
    python -m venv env
)

echo 激活虚拟环境...
call env\Scripts\activate

REM 安装项目依赖
if exist "requirements.txt" (
    echo 安装项目依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 警告: 依赖安装过程中出现问题，但仍尝试启动应用。
        pause
    )
)

REM 提示用户输入ComfyUI路径（如果尚未配置）
set "COMFYUI_PATH="
set /p COMFYUI_PATH="请输入ComfyUI安装路径（直接回车使用已有配置）: "

REM 如果用户提供了新的ComfyUI路径，更新配置文件
if not "%COMFYUI_PATH%" == "" (
    echo 更新ComfyUI配置...
    python -c "import json, os; config_path = os.path.join('configs', 'config.json'); with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f); config['comfyui']['path'] = '%COMFYUI_PATH%'; with open(config_path, 'w', encoding='utf-8') as f: json.dump(config, f, ensure_ascii=False, indent=2)"
    if errorlevel 1 (
        echo 警告: ComfyUI配置更新失败，但仍尝试启动应用。
        pause
    ) else (
        echo ComfyUI配置已更新。
    )
)

REM 启动Flask应用
cd scripts
if exist "app_flask.py" (
    echo 正在启动AIGC创意平台...
    echo 请等待服务器启动完成，然后在浏览器中访问 http://localhost:5000
    echo.
    echo 注意：请保持此窗口打开，关闭窗口将停止服务器。
    echo.
    
    python app_flask.py
    
    REM 如果应用程序意外退出，显示错误信息
    if errorlevel 1 (
        echo.
        echo 错误: 应用程序启动失败。
        pause
    )
) else (
    echo 错误: 未找到app_flask.py文件。
    pause
)

cd ..
pause