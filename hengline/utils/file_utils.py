#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件处理工具模块
"""
import os
import time
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# 检查文件类型是否允许上传
def allowed_file(filename):
    """检查文件类型是否允许上传"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 保存上传的文件
def save_uploaded_file(file, upload_folder):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        return file_path
    return None


def generate_output_filename(task_type):
    """生成输出文件名"""
    name = f"{task_type}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    if task_type in ['text_to_video', 'image_to_video']:
        name = name + ".mp4"
    elif task_type in ['image_to_image', 'image_to_image_v2']:
        name = name + ".png"

    return name


def is_valid_image_file(file_path: str) -> bool:
    """
    检查文件是否为有效的图片文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否为有效图片文件
    """
    # 检查文件扩展名
    valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
    _, ext = os.path.splitext(file_path.lower())
    return ext in valid_extensions


def file_exists(file_path):
    """检查文件是否存在"""
    path = Path(file_path)
    return path.is_file()
