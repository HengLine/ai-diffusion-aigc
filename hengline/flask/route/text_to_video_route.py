# -*- coding: utf-8 -*-
"""
文生视频路由模块
"""

from flask import Blueprint, render_template

# 导入WorkflowManager
import os
import sys
import time
from flask import Blueprint, render_template, request, jsonify
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 从配置工具获取页面显示的参数（setting节点优先于default节点）
from hengline.utils.config_utils import get_workflow_preset, get_paths_config
# 配置日志
from hengline.logger import warning, error, debug

# 创建Blueprint
text_to_video_bp = Blueprint('text_to_video', __name__)


@text_to_video_bp.route('/text_to_video', methods=['GET'])
def text_to_video():
    """文生视频页面路由"""

    # 从配置工具获取页面显示的参数（setting节点优先于default节点）
    from hengline.utils.config_utils import get_workflow_preset
    display_params = get_workflow_preset('text_to_video', 'setting')
    if not display_params:  # 如果setting节点为空，则使用default节点
        display_params = get_workflow_preset('text_to_video', 'default')

    return render_template('text_to_video.html', default_params=display_params)


