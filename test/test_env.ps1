# 测试虚拟环境创建和激活功能

Write-Host "=== 开始测试虚拟环境创建和激活 ==="

# 检查Python是否安装
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 未找到Python！请确保Python已正确安装并添加到系统PATH。"
    Read-Host -Prompt "按Enter键退出"
    exit 1
}

# 检查env目录是否存在，不存在则创建
if (-not (Test-Path -Path "env")) {
    Write-Host "创建Python虚拟环境..."
    python -m venv env
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 虚拟环境创建失败！"
        Read-Host -Prompt "按Enter键退出"
        exit 1
    }
    Write-Host "虚拟环境创建成功！"
} else {
    Write-Host "虚拟环境已存在，跳过创建步骤。"
}

# 检查激活脚本是否存在
if (Test-Path -Path "env\Scripts\Activate.ps1") {
    Write-Host "激活虚拟环境..."
    & "env\Scripts\Activate.ps1"
    Write-Host "虚拟环境已激活！"
} else {
    Write-Host "错误: 虚拟环境激活脚本不存在！"
    Read-Host -Prompt "按Enter键退出"
    exit 1
}

# 检查pip是否可用
pip --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: pip不可用！"
    Read-Host -Prompt "按Enter键退出"
    exit 1
}

Write-Host "=== 测试完成 ==="
Read-Host -Prompt "按Enter键退出"