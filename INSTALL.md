# AIGC项目安装和使用指南

本指南将帮助您安装和配置AIGC AI生成内容演示项目。

## 前提条件

在开始之前，请确保您的系统满足以下要求：

- Python 3.8 或更高版本
- pip 包管理器
- 足够的磁盘空间用于存储模型和生成结果
- 推荐配置：具有CUDA支持的NVIDIA GPU（用于加速生成过程）

## 安装步骤

### 1. 安装 ComfyUI

本项目基于 ComfyUI 工作流，因此您需要先安装 ComfyUI：

1. 从 GitHub 克隆 ComfyUI 仓库：
   ```
   git clone https://github.com/comfyanonymous/ComfyUI.git
   ```

2. 安装 ComfyUI 依赖：
   ```
   cd ComfyUI
   pip install -r requirements.txt
   ```

3. 下载所需的模型文件（如 SD、SVD、Flux 等），并将它们放置在 ComfyUI 的相应目录中：
   - SD 模型：放置在 `ComfyUI/models/checkpoints/` 目录
   - VAE 模型：放置在 `ComfyUI/models/vae/` 目录
   - LoRA 模型：放置在 `ComfyUI/models/loras/` 目录
   - ControlNet 模型：放置在 `ComfyUI/models/controlnet/` 目录

### 2. 安装本项目

1. 克隆或下载本项目到您的计算机：
   ```
   git clone <项目仓库地址>
   cd ai-aigc-demo
   ```

2. 安装项目依赖：
   ```
   pip install -r requirements.txt
   ```

## 配置项目

### 1. 修改配置文件

打开 `configs/config.json` 文件，根据您的环境修改以下配置：

- `comfyui.path`：设置为您的 ComfyUI 安装路径
- `models` 部分：设置各种模型的路径和默认模型名称
- `settings` 部分：根据需要调整生成参数

### 2. 准备工作流文件

项目已经包含了两个预设的工作流文件：
- `workflows/ancient_clothing_workflow.json`：古装图片生成工作流
- `workflows/sci_fi_video_workflow.json`：科幻视频生成工作流

您可以根据需要修改这些工作流文件，或者创建新的工作流文件。

## 使用方法

### 方法一：使用Web界面（推荐）

1. 双击运行 `start_app.bat` 脚本（Windows系统），或者在终端中执行：
   ```
   python scripts/app.py
   ```

2. 脚本会自动安装依赖并启动Web界面。

3. 在浏览器中打开显示的URL（通常是 http://localhost:8501）。

4. 在Web界面中，首先配置 ComfyUI 路径，然后选择相应的功能标签页：
   - **文生图**：通过文本描述生成图像
   - **图生图**：基于输入图像生成新的图像变体
   - **图生视频**：将静态图像转换为动态视频
   - **古装图片生成**：生成中国传统风格的古装图片
   - **科幻视频生成**：生成未来科幻风格的视频

### 方法二：使用命令行工具

您也可以直接使用 `run_workflow.py` 脚本通过命令行运行特定的工作流：

```
python scripts/run_workflow.py --comfyui-path "<您的ComfyUI路径>" --app ancient_clothing --prompt "美丽的古代女子"
```

或者运行自定义工作流：

```
python scripts/run_workflow.py --comfyui-path "<您的ComfyUI路径>" --workflow "workflows/your_workflow.json" --prompt "您的提示词"
```

## 项目结构说明

- `workflows/`：存储 ComfyUI 工作流文件
- `scripts/`：存储项目的主要脚本文件
- `configs/`：存储配置文件
- `outputs/`：存储生成的结果文件
- `requirements.txt`：列出项目依赖的 Python 包
- `start_app.bat`：Windows 启动脚本

## 常见问题解答

### Q: 运行时提示 "ComfyUI路径不存在"？
A: 请确保在Web界面的配置中正确设置了ComfyUI的安装路径。

### Q: 生成过程很慢？
A: 生成速度取决于您的硬件配置。如果没有GPU加速，生成过程可能会比较慢。建议在具有CUDA支持的NVIDIA GPU上运行。

### Q: 如何添加新的工作流？
A: 在 ComfyUI 中创建并导出您的工作流，然后将其保存到 `workflows/` 目录中。

### Q: 如何添加新的模型？
A: 将模型文件放置在 ComfyUI 相应的模型目录中，然后更新 `configs/config.json` 文件中的模型配置。

## 注意事项

- 本项目使用的AI模型可能需要大量的计算资源，尤其是在生成视频时。
- 生成的内容应遵守相关法律法规，不得用于非法用途。
- 定期更新您的模型文件以获得更好的生成效果。
- 如果您在使用过程中遇到问题，可以查看 ComfyUI 的官方文档或提交 Issue。