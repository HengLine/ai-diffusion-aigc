#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件处理工具模块
"""
import os
from werkzeug.utils import secure_filename
from flask import flash, redirect, url_for

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