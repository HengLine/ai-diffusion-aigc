# ComfyUI工作流调用指南

本文档详细介绍了AIGC创意平台如何与ComfyUI进行集成，实现AI图像和视频生成功能。

## 实现原理

我们对代码进行了全面改造，将原先的模拟结果生成替换为实际调用ComfyUI工作流的功能：

1. **API交互机制**：使用`requests`库与ComfyUI的REST API进行交互
2. **工作流管理**：通过加载、更新和运行JSON格式的工作流文件
3. **完整的错误处理**：包含服务器状态检查、请求重试和详细日志

## 主要更改

### 1. run_workflow.py的增强

我们完全重写了`ComfyUIRunner`类的`run_workflow`方法，添加了以下核心功能：

- **服务器状态检查**：自动检测ComfyUI服务器是否正在运行
- **工作流提交**：将工作流JSON提交到ComfyUI的`/prompt`端点
- **异步处理**：等待工作流处理完成并获取结果
- **输出管理**：从ComfyUI获取生成的图像或视频并保存到本地

### 2. app.py的功能实现

我们修改了三个主要标签页，使其能够实际调用ComfyUI工作流：

- **文生图**：加载`text_to_image_basic.json`工作流，应用用户输入的提示词和参数
- **图生图**：加载`image_to_image_basic.json`工作流，处理上传的图像和风格转换参数
- **图生视频**：使用已有的科幻视频生成功能处理上传的图像

### 3. 参数更新机制

我们改进了`update_workflow_params`方法，使其能够智能识别并更新工作流中的各种节点参数：

- **提示词节点**：更新CLIPTextEncode节点的text参数
- **图像大小节点**：调整EmptyLatentImage节点的width和height参数
- **采样器节点**：设置KSampler节点的steps、cfg和denoising_strength参数
- **图像加载节点**：指定LoadImage节点的image路径参数

## 使用说明

### 前提条件

1. 确保已安装ComfyUI并配置了正确的路径
2. 在应用的配置页面设置正确的ComfyUI安装路径
3. 确保ComfyUI包含所需的模型和节点

### 操作步骤

1. **启动应用**：运行`start_app.bat`启动Streamlit应用
2. **配置ComfyUI**：在应用的"⚙️ ComfyUI配置"部分设置正确的ComfyUI路径
3. **选择功能**：选择"文生图"、"图生图"或"图生视频"标签页
4. **设置参数**：输入提示词、调整参数或上传图像
5. **生成内容**：点击"生成"按钮，应用会自动连接ComfyUI并执行工作流
6. **查看结果**：生成完成后，结果图像或视频会显示在界面上

## 工作流文件说明

应用使用以下工作流文件（位于`workflows`目录）：

- `text_to_image_basic.json`：用于文生图功能
- `image_to_image_basic.json`：用于图生图功能
- `ancient_clothing_workflow.json`：用于古装图片生成（如不存在则使用text_to_image_basic）
- `sci_fi_video_workflow.json`：用于科幻视频和图生视频功能

## 配置文件说明

应用的主要配置位于`configs/config.json`文件中：

- `comfyui.path`：ComfyUI的安装路径
- `comfyui.api_url`：ComfyUI API的URL（通常为http://127.0.0.1:8188）
- `settings`：各功能模块的默认参数设置

## 故障排除

### 常见问题与解决方案

1. **ComfyUI服务器未运行**
   - 应用会尝试自动启动ComfyUI服务器
   - 如果自动启动失败，请手动启动ComfyUI，然后刷新页面

2. **工作流文件不存在**
   - 确保`workflows`目录中包含所需的JSON工作流文件
   - 文生图功能会尝试使用备用工作流

3. **图像/视频生成失败**
   - 检查ComfyUI控制台输出以获取详细错误信息
   - 确保ComfyUI已安装所需的模型和依赖
   - 尝试调整参数，减少图像尺寸或降低步数

4. **结果文件无法显示**
   - 检查`outputs`目录中是否存在生成的文件
   - 确认文件格式正确（图像为PNG/JPG，视频为MP4）

## 高级功能

### 自定义工作流

您可以通过以下方式自定义工作流：

1. 在ComfyUI中创建和调整工作流
2. 导出为JSON文件并保存到`workflows`目录
3. 在应用中选择相应的功能来使用自定义工作流

### 批量生成

通过修改代码，您可以实现批量生成功能：

1. 创建提示词列表或参数组合
2. 循环调用相应的生成方法
3. 保存每个生成结果到不同的文件

## 最佳实践

1. **参数优化**：根据不同的内容类型调整参数
   - 高质量图像：增加步数（20-30步）和CFG值（7-10）
   - 快速预览：减少步数（10-15步）和CFG值（5-7）

2. **提示词工程**：编写清晰、具体的提示词
   - 使用形容词描述视觉效果（如"ultra detailed", "vibrant colors"）
   - 指定艺术风格（如"digital painting", "anime style"）
   - 包含构图元素（如"wide angle", "cinematic lighting"）

3. **服务器管理**：定期检查ComfyUI服务器状态
   - 长时间运行后重启服务器以释放内存
   - 监控资源使用情况，避免同时运行过多任务