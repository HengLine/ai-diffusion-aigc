@echo off
chcp 65001 >nul

rem 测试虚拟环境创建和依赖安装

rem 在本地创建Python虚拟环境
if not exist "env" (
    echo 正在创建Python虚拟环境...
    "%SystemRoot%\System32\where.exe" python > tmp_python_path.txt
    set /p PYTHON_PATH=<tmp_python_path.txt
    del tmp_python_path.txt
    
    if exist "%PYTHON_PATH%" (
        echo 使用Python路径: %PYTHON_PATH%
        "%PYTHON_PATH%" -m venv env
    ) else (
        echo 未找到Python安装！请确保Python已正确安装并添加到系统PATH。
        pause
        exit /b 1
    )
)

rem 激活虚拟环境
echo 正在激活虚拟环境...
if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
) else (
    echo 虚拟环境激活脚本不存在！
    pause
    exit /b 1
)

if %errorlevel% neq 0 (
    echo 虚拟环境激活失败！
    pause
    exit /b %errorlevel%
)

rem 检查pip是否可用
echo 检查pip版本...
pip --version

rem 安装依赖
echo 正在安装依赖包...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo 依赖包安装失败！
    pause
    exit /b %errorlevel%
)

echo 测试完成！虚拟环境已创建并激活，依赖包已安装。
pause