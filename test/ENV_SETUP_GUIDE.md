# AIGC演示应用环境设置指南

由于在Trae AI环境中运行批处理脚本存在限制，建议在本地开发环境中按照以下步骤手动设置Python虚拟环境并运行应用。

## 步骤1: 创建Python虚拟环境

在项目根目录下打开命令提示符或PowerShell窗口，执行以下命令创建虚拟环境：

```batch
# Windows命令提示符
python -m venv env

# 或者使用PowerShell
python -m venv env
```

## 步骤2: 激活虚拟环境

创建完成后，激活虚拟环境：

```batch
# Windows命令提示符
env\Scripts\activate.bat

# Windows PowerShell
env\Scripts\Activate.ps1
```

激活成功后，命令提示符前会显示`(env)`字样。

## 步骤3: 安装项目依赖

在激活的虚拟环境中，执行以下命令安装项目所需的所有依赖包：

```batch
pip install -r requirements.txt
```

## 步骤4: 运行应用程序

依赖包安装完成后，执行以下命令启动AIGC演示应用：

```batch
streamlit run scripts\app.py
```

应用启动后，会在默认浏览器中自动打开Web界面，或在命令行中显示访问URL（通常是 http://localhost:8501）。

## 优化后的启动脚本

我们已经优化了`start_app.bat`脚本，在本地环境中可以直接双击运行，它会自动执行上述所有步骤：

1. 检查Python是否安装
2. 创建虚拟环境（如果不存在）
3. 激活虚拟环境
4. 安装依赖包
5. 启动应用程序

## 故障排除

如果遇到问题，请检查以下几点：

1. **Python未找到**：确保Python已正确安装并添加到系统PATH环境变量中
2. **虚拟环境创建失败**：尝试以管理员身份运行命令提示符/PowerShell
3. **依赖安装失败**：检查网络连接，或尝试使用国内镜像源
4. **Streamlit启动失败**：确保所有依赖包都已正确安装

## 其他相关脚本

项目中还包含以下脚本：

- `simple_start.bat`：极简版本的启动脚本
- `start_flask_app.bat`：启动Flask版本的Web界面

需要时可以根据实际情况选择使用。