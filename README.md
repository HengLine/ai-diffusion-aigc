# AIGC AI 生成内容演示项目

# AIGC创意平台

这是一个功能丰富的AIGC（人工智能生成内容）平台，基于ComfyUI工作流，集成了多种先进的AI生成模型，实现了文生图、图生图、文生视频、图生视频等多种创意生成功能。

## 1. 系统介绍

### 核心功能

- **文生图**：通过文本描述生成高质量图像
- **图生图**：基于输入图像生成新的图像变体
- **文生视频**：通过文本描述生成高质量视频
- **图生视频**：将静态图像转换为动态视频
- **特定场景应用**：
  - 科幻视频生成
  - 更多场景持续开发中...

### 技术架构

- **底层框架**：基于ComfyUI工作流引擎，提供强大的模型编排能力
- **支持模型**：集成SD (Stable Diffusion)、SVD (Stable Video Diffusion)、Flux、Wan等多种先进生成模型
- **双界面设计**：同时提供Streamlit和Flask两种Web界面，满足不同使用习惯
- **模块化设计**：采用组件化架构，易于扩展新功能和场景
- **任务队列**：支持异步任务处理和重试机制，提高系统稳定性

### 项目结构

```
├── hengline/        # 核心代码目录
│   ├── app_streamlit.py  # Streamlit应用入口
│   ├── flask/       # Flask应用相关代码
│   ├── streamlit/   # Streamlit界面组件
│   └── utils/       # 工具函数库
├── workflows/       # ComfyUI工作流配置文件
├── configs/         # 系统配置文件
├── imgs/            # 效果图和示例图片
├── start_app.py     # Streamlit应用启动脚本
├── start_flask.py   # Flask应用启动脚本
└── requirements.txt # 项目依赖文件
```

## 2. 安装步骤

### 前提条件

- Python 3.8 或更高版本
- pip 包管理器
- 足够的磁盘空间用于存储模型和生成结果
- 推荐配置：具有CUDA支持的NVIDIA GPU（用于加速生成过程）

### 安装过程

#### 步骤1：安装ComfyUI

本项目基于ComfyUI工作流，首先需要安装ComfyUI：

1. 从GitHub克隆ComfyUI仓库：
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI.git
   ```

2. 安装ComfyUI依赖：
   ```bash
   cd ComfyUI
   pip install -r requirements.txt
   ```

3. 下载所需的模型文件（如SD、SVD、Flux、Wan等），并放置在ComfyUI/models 的相应目录中：
   
   > 1. **文生图、图生图**（共约2G）：
   >
   >    /**checkpoints**/==v1-5-pruned-emaonly-fp16.safetensors==
   >    下载路径（https://hf-mirror.com/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/v1-5-pruned-emaonly-fp16.safetensors）
   >
   >    
   >
   > 2. **图生视频**（共约18G）：
   >
   >    - /**checkpoints**/==ltx-video-2b-v0.9.safetensors==	
   >      下载路径（https://hf-mirror.com/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.safetensors）
   >    - /**text_encoders**/==t5xxl_fp16.safetensors==		
   >      下载路径（https://hf-mirror.com/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors）
   >
   >    
   >
   > 3. **文生视频**（共约35G）：
   >
   >    - /**text_encoders**/==umt5_xxl_fp8_e4m3fn_scaled.safetensors==	
   >      下载路径（https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors）
   >    - /**vae**/==wan_2.1_vae.safetensors==	
   >      下载路径（https://hf-mirror.com/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors）
   >    - /**diffusion_models**/==wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors==	
   >      下载路径（https://hf-mirror.com/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors）
   >    - /**diffusion_models**/==wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors==
   >      下载路径（https://hf-mirror.com/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors）
   >    - /**loras**/==wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors==
   >      下载路径（https://hf-mirror.com/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors）
   >    - /**loras**/==wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors==
   >      下载路径（https://hf-mirror.com/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors）

#### 步骤2：安装本项目

1. 克隆或下载本项目到您的计算机：
   ```bash
   git clone <项目仓库地址>
   cd ai-diffusion-aigc
   ```

2. 使用提供的启动脚本自动完成安装：
   - 对于Streamlit界面：运行`start_app.py`
   - 对于Flask界面：运行`start_flask.py`

   启动脚本将自动：
   - 检查Python环境
   - 创建/激活虚拟环境（./venv）
   - 安装项目依赖
   - 启动相应的Web服务

## 3. 使用说明

### 配置系统

1. 修改配置文件：
   打开`configs/config.json`文件，根据您的环境修改以下配置：
   - `comfyui.api_url`：设置为您的ComfyUI URL
   - `user`部分：设置用户接收的邮箱
   - `settings`部分：根据需要调整生成参数

2. 工作流配置：
   项目包含多个预设的工作流文件，存放在`workflows/`目录中，您可以根据需要修改或创建新的工作流。

### 启动应用

#### 方法一：使用Streamlit界面

1. 运行启动脚本：
   ```bash
   python start_app.py
   ```

2. 脚本会自动安装依赖并启动Web界面。

3. 在浏览器中打开显示的URL（通常是http://localhost:8501）。

4. 在Web界面中，配置相关参数后即可使用各项功能。

#### 方法二：使用Flask界面

1. 运行启动脚本：
   ```bash
   python start_flask.py
   ```

2. 在浏览器中打开显示的URL（通常是http://localhost:5000）。

3. 在Web界面中，配置相关参数后即可使用各项功能。

### 功能使用

- **文生图**：输入文本描述，调整相关参数，点击生成按钮获取图像结果
- **图生图**：上传参考图像，输入文本描述，调整参数后生成新图像
- **文生视频**：输入文本描述，调整相关参数，点击生成按钮获取动态视频
- **图生视频**：上传静态图像，设置视频参数，生成动态视频

## 4. 效果图展示

### Streamlit界面效果图

![Streamlit主界面](/imgs/image-20250904161528032.png)

#### 文生图效果

![文生图效果](/imgs/image-20250903230925512.png)

#### 图生图效果

![图生图效果](/imgs/image-20250903232341349.png)

### Flask界面效果图

![Flask主界面](/imgs/image-20250904161336645.png)

#### 文生图效果

![Flask文生图效果](/imgs/image-20250904163923815.png)

#### 图生图效果

![Flask图生图效果](/imgs/image-20250904164853358.png)

### 视频生成功能（开发中）

文生视频和图生视频功能正在持续开发和优化中，敬请期待！





## 5. 注意事项

- 本项目使用的AI模型可能需要大量的计算资源，尤其是在生成视频时。
- 生成的内容应遵守相关法律法规，不得用于非法用途。
- 定期更新您的模型文件以获得更好的生成效果。
- 如果您在使用过程中遇到问题，可以查看 ComfyUI 的官方文档或提交 Issue。
