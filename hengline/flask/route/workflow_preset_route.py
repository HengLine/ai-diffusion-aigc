# -*- coding: utf-8 -*-
"""
@FileName: workflow_preset_route.py
@Description: 工作流预设路由模块，负责处理自定义工作流的保存、获取和管理
@Author: HengLine
@Time: 2025/08 - 2025/11
"""

import json
import os
import sys
import time

from flask import Blueprint, request, jsonify

# 导入日志模块
from hengline.logger import debug, info, error

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 创建Blueprint
workflow_preset_bp = Blueprint('workflow_preset', __name__)

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 工作流预设目录路径
WORKFLOW_PRESET_DIR = os.path.join(project_root, 'workflows', 'preset')
# 工作流预设配置文件路径
WORKFLOW_PRESETS_CONFIG = os.path.join(project_root, 'configs', 'workflow_presets.json')

# 确保工作流预设目录存在
if not os.path.exists(WORKFLOW_PRESET_DIR):
    os.makedirs(WORKFLOW_PRESET_DIR)


def load_workflow_presets():
    """加载工作流预设配置文件"""
    try:
        if os.path.exists(WORKFLOW_PRESETS_CONFIG):
            with open(WORKFLOW_PRESETS_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 如果文件不存在，返回空字典
            return {}
    except Exception as e:
        error(f"加载工作流预设配置文件失败: {e}")
        return {}


def save_workflow_presets(config):
    """保存工作流预设配置文件"""
    try:
        with open(WORKFLOW_PRESETS_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        error(f"保存工作流预设配置文件失败: {e}")
        return False


@workflow_preset_bp.route('/workflows/preset/list', methods=['GET'])
def list_workflow_presets():
    """获取工作流预设列表"""
    try:
        # 获取工作流类型
        workflow_type = request.args.get('type', '')
        
        if not workflow_type:
            return jsonify({'success': False, 'message': '工作流类型不能为空'}), 400
        
        # 获取指定类型的工作流预设文件列表
        preset_files = []
        for filename in os.listdir(WORKFLOW_PRESET_DIR):
            if filename.startswith(f'{workflow_type}__') and filename.endswith('.json'):
                # 提取工作流名称（不包含时间戳）
                # 格式：类型__年月日_时分秒.json
                # 例如：text_to_image__20250910_112053.json
                # 我们只保留文件名中的类型部分，去掉时间戳
                # name = filename[:-18]  # 18 = 9（时间戳长度） + 5（.json长度）
                preset_files.append(filename)
        
        return jsonify(preset_files)
    except Exception as e:
        error(f"获取工作流预设列表失败: {e}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@workflow_preset_bp.route('/workflows/preset/save', methods=['POST'])
def save_workflow():
    """保存工作流配置"""
    try:
        # 获取请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': '请求数据不能为空'}), 400
        
        # 验证必要字段
        workflow_type = data.get('type', '')
        workflow_json = data.get('json', '')
        workflow_name_param = data.get('name', '')
        
        if not workflow_type:
            return jsonify({'success': False, 'message': '工作流类型不能为空'}), 400
        
        if not workflow_json:
            return jsonify({'success': False, 'message': '工作流JSON配置不能为空'}), 400
        
        # 验证JSON格式
        try:
            parsed_json = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            return jsonify({'success': False, 'message': f'JSON格式错误: {str(e)}'}), 400
        
        workflow_name = ''
        file_path = ''
        
        if workflow_name_param:
            # 如果提供了name参数，表示更新现有工作流
            # 查找匹配的工作流文件
            for filename in os.listdir(WORKFLOW_PRESET_DIR):
                if filename.startswith(workflow_name_param) and filename.endswith('.json'):
                    file_path = os.path.join(WORKFLOW_PRESET_DIR, filename)
                    workflow_name = workflow_name_param
                    break
            
            if not file_path:
                # 如果没有找到匹配的文件，则创建新文件
                timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
                filename = f'{workflow_type}__{timestamp}.json'
                file_path = os.path.join(WORKFLOW_PRESET_DIR, filename)
                workflow_name = filename  # 保存完整的文件名
        else:
            # 生成新文件名：类型__年月日_时分秒.json
            timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
            filename = f'{workflow_type}__{timestamp}.json'
            file_path = os.path.join(WORKFLOW_PRESET_DIR, filename)
            workflow_name = filename  # 保存完整的文件名
        
        # 保存工作流文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(workflow_json)
        
        # 更新workflow_presets.json文件
        presets_config = load_workflow_presets()
        # 确保类型节点存在
        if workflow_type not in presets_config:
            presets_config[workflow_type] = {
                'default': {},
                'setting': {},
                'workflow': ''
            }
        
        # 这里我们不自动设置workflow字段，让用户手动选择通过前端的应用按钮来设置
        
        # 确保返回完整的文件名，以便前端能够正确更新workflow节点
        return jsonify({'success': True, 'message': '工作流保存成功', 'workflowName': filename})
    except Exception as e:
        error(f"保存工作流失败: {e}")
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500


@workflow_preset_bp.route('/workflows/preset/get', methods=['GET'])
def get_workflow():
    """获取工作流详情"""
    try:
        # 获取参数
        workflow_type = request.args.get('type', '')
        workflow_name = request.args.get('name', '')
        
        if not workflow_type or not workflow_name:
            return jsonify({'success': False, 'message': '工作流类型和名称不能为空'}), 400
        
        # 查找匹配的工作流文件
        workflow_file = None
        for filename in os.listdir(WORKFLOW_PRESET_DIR):
            if filename.startswith(workflow_name) and filename.endswith('.json'):
                workflow_file = filename
                break
        
        if not workflow_file:
            return jsonify({'success': False, 'message': '未找到指定的工作流'}), 404
        
        # 读取工作流文件
        file_path = os.path.join(WORKFLOW_PRESET_DIR, workflow_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_json = json.load(f)
        
        return jsonify({'success': True, 'json': workflow_json})
    except Exception as e:
        error(f"获取工作流详情失败: {e}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@workflow_preset_bp.route('/workflows/preset/get_current', methods=['GET'])
def get_current_workflow():
    """获取当前工作流类型的workflow节点值"""
    try:
        # 获取工作流类型
        workflow_type = request.args.get('type', '')
        
        if not workflow_type:
            return jsonify({'success': False, 'message': '工作流类型不能为空'}), 400
        
        # 加载当前配置
        presets_config = load_workflow_presets()
        
        # 获取workflow节点值
        workflow = ''
        if workflow_type in presets_config:
            workflow = presets_config[workflow_type].get('workflow', '')
        
        return jsonify({'success': True, 'workflow': workflow})
    except Exception as e:
        error(f"获取当前工作流配置失败: {e}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@workflow_preset_bp.route('/workflows/preset/set', methods=['POST'])
def set_workflow():
    """设置工作流到配置文件"""
    try:
        # 获取请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': '请求数据不能为空'}), 400
        
        # 验证必要字段
        workflow_type = data.get('type', '')
        workflow = data.get('workflow', '')
        
        if not workflow_type:
            return jsonify({'success': False, 'message': '工作流类型不能为空'}), 400
        
        debug(f"接收到的应用工作流请求: type={workflow_type}, workflow={workflow}")
        
        # 加载当前配置
        presets_config = load_workflow_presets()
        debug(f"加载的当前配置: {presets_config}")
        
        # 确保类型节点存在
        if workflow_type not in presets_config:
            presets_config[workflow_type] = {
                'default': {},
                'setting': {},
                'workflow': ''
            }
            debug(f"为类型 {workflow_type} 创建了新的配置节点")
        
        # 设置workflow字段
        presets_config[workflow_type]['workflow'] = workflow
        debug(f"更新后的配置: {presets_config}")
        
        # 保存配置
        if save_workflow_presets(presets_config):
            info(f"工作流配置已成功保存到 {WORKFLOW_PRESETS_CONFIG}")
            return jsonify({'success': True, 'message': '工作流配置已更新'})
        else:
            error(f"保存工作流配置到 {WORKFLOW_PRESETS_CONFIG} 失败")
            return jsonify({'success': False, 'message': '保存工作流配置失败'}), 500
    except Exception as e:
        error(f"设置工作流配置失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'设置失败: {str(e)}'}), 500