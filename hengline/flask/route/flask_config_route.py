# -*- coding: utf-8 -*-
"""
配置页面路由模块
负责处理配置页面的显示和提交逻辑
"""

import json
import os
import sys

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工作流管理器
# 导入配置工具
from hengline.utils.config_utils import get_config, get_comfyui_api_url, get_settings_config, \
    reload_config, get_user_configs

# 创建Blueprint
config_bp = Blueprint('config', __name__)


@config_bp.route('/config', methods=['GET', 'POST'])
def configure():
    """配置页面路由"""

    if request.method == 'POST':
        # 获取表单数据
        email = request.form.get('email', '').strip()
        nickname = request.form.get('nickname', '').strip()
        organization = request.form.get('organization', '').strip()
        comfyui_api_url = request.form.get('comfyui_api_url', '').strip()

        # 验证必填字段
        if not email or not nickname or not comfyui_api_url:
            flash('请填写所有必填字段（电子邮箱、用户昵称和ComfyUI API URL）！', 'error')
            return redirect(url_for('config.configure'))

        # 获取当前配置
        current_config = get_config()

        # 确保settings节点存在
        if 'settings' not in current_config:
            current_config['settings'] = {}
        
        # 保存用户信息配置
        user_config = get_user_configs()
        user_config['email'] = email
        user_config['nickname'] = nickname
        user_config['organization'] = organization
        current_config['settings']['user'] = user_config

        # 保存ComfyUI配置
        from hengline.utils.config_utils import get_comfyui_config
        comfyui_config = get_comfyui_config()
        comfyui_config['api_url'] = comfyui_api_url
        current_config['settings']['comfyui'] = comfyui_config

        # 模型参数配置将通过各个任务类型的设置函数进行更新

        # 验证模型参数
        validation_errors = []

        # 验证文生图参数
        text_to_image_width = request.form.get('settings[text_to_image][width]', '').strip()
        text_to_image_height = request.form.get('settings[text_to_image][height]', '').strip()
        text_to_image_steps = request.form.get('settings[text_to_image][steps]', '').strip()
        text_to_image_cfg = request.form.get('settings[text_to_image][cfg]', '').strip()

        if not text_to_image_width or not text_to_image_height or not text_to_image_steps or not text_to_image_cfg:
            validation_errors.append('文生图：请填写所有必填字段（宽度、高度、步数、CFG值）！')

        # 验证图生图参数
        image_to_image_width = request.form.get('settings[image_to_image][width]', '').strip()
        image_to_image_height = request.form.get('settings[image_to_image][height]', '').strip()
        image_to_image_steps = request.form.get('settings[image_to_image][steps]', '').strip()
        image_to_image_cfg = request.form.get('settings[image_to_image][cfg]', '').strip()

        if not image_to_image_width or not image_to_image_height or not image_to_image_steps or not image_to_image_cfg:
            validation_errors.append('图生图：请填写所有必填字段（宽度、高度、步数、CFG值）！')

        # 验证文生视频参数
        text_to_video_width = request.form.get('settings[text_to_video][width]', '').strip()
        text_to_video_height = request.form.get('settings[text_to_video][height]', '').strip()
        text_to_video_length = request.form.get('settings[text_to_video][length]', '').strip()
        text_to_video_fps = request.form.get('settings[text_to_video][fps]', '').strip()
        text_to_video_cfg = request.form.get('settings[text_to_video][cfg]', '').strip()
        text_to_video_steps = request.form.get('settings[text_to_video][steps]', '').strip()

        if not text_to_video_width or not text_to_video_height or not text_to_video_length or not text_to_video_fps or not text_to_video_cfg or not text_to_video_steps:
            validation_errors.append('文生视频：请填写所有必填字段（宽度、高度、视频长度、帧率、CFG值、步数）！')

        # 验证图生视频参数
        image_to_video_width = request.form.get('settings[image_to_video][width]', '').strip()
        image_to_video_height = request.form.get('settings[image_to_video][height]', '').strip()
        image_to_video_length = request.form.get('settings[image_to_video][length]', '').strip()
        image_to_video_fps = request.form.get('settings[image_to_video][fps]', '').strip()
        image_to_video_cfg = request.form.get('settings[image_to_video][cfg]', '').strip()
        image_to_video_steps = request.form.get('settings[image_to_video][steps]', '').strip()

        if not image_to_video_width or not image_to_video_height or not image_to_video_length or not image_to_video_fps or not image_to_video_cfg or not image_to_video_steps:
            validation_errors.append('图生视频：请填写所有必填字段（宽度、高度、视频长度、帧率、CFG值、步数）！')

        # 如果有验证错误，显示错误消息并返回
        if validation_errors:
            for error in validation_errors:
                flash(error, 'error')
            return redirect(url_for('config.configure'))

        # 处理文生图参数
        from hengline.utils.config_utils import get_task_settings
        text_to_image_params = get_task_settings('text_to_image')
        text_to_image_params['width'] = int(
            request.form.get('settings[text_to_image][width]', text_to_image_params.get('width', 1024)))
        text_to_image_params['height'] = int(
            request.form.get('settings[text_to_image][height]', text_to_image_params.get('height', 1024)))
        text_to_image_params['steps'] = int(
            request.form.get('settings[text_to_image][steps]', text_to_image_params.get('steps', 20)))
        text_to_image_params['cfg'] = float(
            request.form.get('settings[text_to_image][cfg]', text_to_image_params.get('cfg', 8.0)))
        text_to_image_params['batch_size'] = int(
            request.form.get('settings[text_to_image][batch_size]', text_to_image_params.get('batch_size', 1)))
        text_to_image_params['seed'] = int(
            request.form.get('settings[text_to_image][seed]', text_to_image_params.get('seed', -1)))
        text_to_image_params['prompt'] = request.form.get('settings[text_to_image][prompt]',
                                                          text_to_image_params.get('prompt', ''))
        text_to_image_params['negative_prompt'] = request.form.get('settings[text_to_image][negative_prompt]',
                                                                   text_to_image_params.get('negative_prompt', ''))

        # 处理图生图参数
        image_to_image_params = get_task_settings('image_to_image')
        image_to_image_params['width'] = int(
            request.form.get('settings[image_to_image][width]', image_to_image_params.get('width', 1024)))
        image_to_image_params['height'] = int(
            request.form.get('settings[image_to_image][height]', image_to_image_params.get('height', 1024)))
        image_to_image_params['steps'] = int(
            request.form.get('settings[image_to_image][steps]', image_to_image_params.get('steps', 20)))
        image_to_image_params['cfg'] = float(
            request.form.get('settings[image_to_image][cfg]', image_to_image_params.get('cfg', 8.0)))
        image_to_image_params['batch_size'] = int(
            request.form.get('settings[image_to_image][batch_size]', image_to_image_params.get('batch_size', 1)))
        image_to_image_params['seed'] = int(
            request.form.get('settings[image_to_image][seed]', image_to_image_params.get('seed', -1)))
        image_to_image_params['denoise'] = float(
            request.form.get('settings[image_to_image][denoise]',
                             image_to_image_params.get('denoise', 0.7)))
        image_to_image_params['prompt'] = request.form.get('settings[image_to_image][prompt]',
                                                           image_to_image_params.get('prompt', ''))
        image_to_image_params['negative_prompt'] = request.form.get('settings[image_to_image][negative_prompt]',
                                                                    image_to_image_params.get('negative_prompt', ''))

        # 处理文生视频参数
        text_to_video_params = get_task_settings('text_to_video')
        text_to_video_params['width'] = int(
            request.form.get('settings[text_to_video][width]', text_to_video_params.get('width', 576)))
        text_to_video_params['height'] = int(
            request.form.get('settings[text_to_video][height]', text_to_video_params.get('height', 320)))
        text_to_video_params['length'] = int(
            request.form.get('settings[text_to_video][length]', text_to_video_params.get('length', 121)))
        text_to_video_params['fps'] = int(
            request.form.get('settings[text_to_video][fps]', text_to_video_params.get('fps', 16)))
        text_to_video_params['shift'] = int(
            request.form.get('settings[text_to_video][shift]', text_to_video_params.get('shift', 8)))
        text_to_video_params['batch_size'] = int(
            request.form.get('settings[text_to_video][batch_size]', text_to_video_params.get('batch_size', 1)))
        text_to_video_params['denoise'] = float(
            request.form.get('settings[text_to_video][denoise]', text_to_video_params.get('denoise', 1)))
        text_to_video_params['seed'] = int(
            request.form.get('settings[text_to_video][seed]', text_to_video_params.get('seed', -1)))
        text_to_video_params['cfg'] = float(
            request.form.get('settings[text_to_video][cfg]', text_to_video_params.get('cfg', 1)))
        text_to_video_params['prompt'] = request.form.get('settings[text_to_video][prompt]',
                                                          text_to_video_params.get('prompt', ''))
        text_to_video_params['negative_prompt'] = request.form.get('settings[text_to_video][negative_prompt]',
                                                                   text_to_video_params.get('negative_prompt', ''))

        # 处理图生视频参数
        image_to_video_params = get_task_settings('image_to_video')
        image_to_video_params['width'] = int(
            request.form.get('settings[image_to_video][width]', image_to_video_params.get('width', 512)))
        image_to_video_params['height'] = int(
            request.form.get('settings[image_to_video][height]', image_to_video_params.get('height', 384)))
        image_to_video_params['length'] = int(
            request.form.get('settings[image_to_video][length]', image_to_video_params.get('length', 121)))
        image_to_video_params['fps'] = int(
            request.form.get('settings[image_to_video][fps]', image_to_video_params.get('fps', 16)))
        image_to_video_params['shift'] = int(
            request.form.get('settings[image_to_video][shift]', image_to_video_params.get('shift', 8)))
        image_to_video_params['batch_size'] = int(
            request.form.get('settings[image_to_video][batch_size]', image_to_video_params.get('batch_size', 1)))
        image_to_video_params['denoise'] = float(
            request.form.get('settings[image_to_video][denoise]', image_to_video_params.get('denoise', 1)))
        image_to_video_params['seed'] = int(
            request.form.get('settings[image_to_video][seed]', image_to_video_params.get('seed', -1)))
        image_to_video_params['cfg'] = float(
            request.form.get('settings[image_to_video][cfg]', image_to_video_params.get('cfg', 1)))
        image_to_video_params['prompt'] = request.form.get('settings[image_to_video][prompt]',
                                                           image_to_video_params.get('prompt', ''))
        image_to_video_params['negative_prompt'] = request.form.get('settings[image_to_video][negative_prompt]',
                                                                    image_to_video_params.get('negative_prompt', ''))

        # 确保配置目录存在
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                  'configs')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # 保存配置到文件
        config_path = os.path.join(config_dir, 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=2)

        # 使用新的预设配置函数保存工作流预设
        from hengline.utils.config_utils import save_workflow_preset
        
        # 保存文生图预设
        save_workflow_preset('text_to_image', text_to_image_params)
        
        # 保存图生图预设
        save_workflow_preset('image_to_image', image_to_image_params)
        
        # 保存文生视频预设
        save_workflow_preset('text_to_video', text_to_video_params)
        
        # 保存图生视频预设
        save_workflow_preset('image_to_video', image_to_video_params)

        # 重新加载配置
        reload_config()

        # 重新初始化运行器
        # workflow_manager.stop_runner()

        flash('配置已成功保存！', 'success')
        return redirect(url_for('config.configure'))

    # 从配置工具获取当前配置
    comfyui_api_url = get_comfyui_api_url()
    user_config = get_user_configs()
    user_email = user_config.get('email', '')
    user_nickname = user_config.get('nickname', '')
    user_organization = user_config.get('organization', '')

    # 获取模型参数配置，使用get_workflow_preset函数确保优先使用setting节点的值
    from hengline.utils.config_utils import get_workflow_preset
    
    # 获取配置，get_workflow_preset已经实现了setting节点优先的逻辑
    settings = {
        'text_to_image': get_workflow_preset('text_to_image'),
        'image_to_image': get_workflow_preset('image_to_image'),
        'text_to_video': get_workflow_preset('text_to_video'),
        'image_to_video': get_workflow_preset('image_to_video')
    }

    return render_template('config.html',
                           comfyui_api_url=comfyui_api_url,
                           user_email=user_email,
                           user_nickname=user_nickname,
                           user_organization=user_organization,
                           settings=settings)


@config_bp.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """配置的API接口"""

    if request.method == 'GET':
        # 获取当前配置，get_settings_config已经实现了配置的加载
        settings = get_settings_config()

        user_config = get_user_configs()

        return jsonify({
            'success': True,
            'data': {
                'comfyui_api_url': get_comfyui_api_url(),
                'user_email': user_config.get('email', ''),
                'user_nickname': user_config.get('nickname', ''),
                'user_organization': user_config.get('organization', ''),
                'settings': settings
            }
        })

    elif request.method == 'POST':
        # 更新配置
        try:
            data = request.json
            # 获取当前配置
            current_config = get_config()

            # 验证必填字段
            if not data.get('email') or not data.get('nickname') or not data.get('comfyui_api_url'):
                return jsonify({
                    'success': False,
                    'message': '请填写所有必填字段（电子邮箱、用户昵称和ComfyUI API URL）！'
                }), 400

            # 保存用户信息配置
            from hengline.utils.config_utils import get_user_config
            user_config = get_user_config()
            user_config['email'] = data.get('email', '').strip()
            user_config['nickname'] = data.get('nickname', '').strip()
            user_config['organization'] = data.get('organization', '').strip()

            # 保存ComfyUI配置
            from hengline.utils.config_utils import get_comfyui_config
            comfyui_config = get_comfyui_config()
            comfyui_config['api_url'] = data.get('comfyui_api_url', '').strip()

            # 保存模型参数配置
            from hengline.utils.config_utils import get_task_settings

            # 如果提交了设置数据，则更新
            if data.get('settings'):
                settings_data = data['settings']
                validation_errors = []

                # 验证并更新文生图参数
                if settings_data.get('text_to_image'):
                    text_to_image = settings_data['text_to_image']
                    if not text_to_image.get('width') or not text_to_image.get('height') or not text_to_image.get(
                            'steps') or text_to_image.get('cfg') is None:
                        validation_errors.append('文生图：请填写所有必填字段（宽度、高度、步数、CFG值）！')

                    text_to_image_params = get_task_settings('text_to_image')
                    text_to_image_params.update(text_to_image)

                # 验证并更新图生图参数
                if settings_data.get('image_to_image'):
                    image_to_image = settings_data['image_to_image']
                    if not image_to_image.get('width') or not image_to_image.get('height') or not image_to_image.get(
                            'steps') or image_to_image.get('cfg') is None:
                        validation_errors.append('图生图：请填写所有必填字段（宽度、高度、步数、CFG值）！')

                    image_to_image_params = get_task_settings('image_to_image')
                    image_to_image_params.update(image_to_image)

                # 验证并更新文生视频参数
                if settings_data.get('text_to_video'):
                    text_to_video = settings_data['text_to_video']
                    if not text_to_video.get('width') or not text_to_video.get('height') or not text_to_video.get(
                            'frames') or not text_to_video.get('fps') or text_to_video.get('cfg') is None or not text_to_video.get('steps'):
                        validation_errors.append('文生视频：请填写所有必填字段（宽度、高度、帧数、帧率、CFG值、步数）！')

                    text_to_video_params = get_task_settings('text_to_video')
                    text_to_video_params.update(text_to_video)

                # 验证并更新图生视频参数
                if settings_data.get('image_to_video'):
                    image_to_video = settings_data['image_to_video']
                    if not image_to_video.get('width') or not image_to_video.get('height') or not image_to_video.get(
                            'frames') or not image_to_video.get('fps') or image_to_video.get('cfg') is None or not image_to_video.get('steps'):
                        validation_errors.append('图生视频：请填写所有必填字段（宽度、高度、帧数、帧率、CFG值、步数）！')

                    image_to_video_params = get_task_settings('image_to_video')
                    image_to_video_params.update(image_to_video)

                # 如果有验证错误，返回错误信息
                if validation_errors:
                    return jsonify({
                        'success': False,
                        'message': '\n'.join(validation_errors)
                    }), 400

            # 确保配置目录存在
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                      'configs')
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # 保存配置到文件
            config_path = os.path.join(config_dir, 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)

            # 重新加载配置
            reload_config()

            # 重新初始化运行器
            # workflow_manager.stop_runner()

            return jsonify({
                'success': True,
                'message': '配置已成功保存！'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'保存配置失败：{str(e)}'
            }), 500


@config_bp.route('/config/reset/<preset_type>', methods=['GET'])
def reset_preset(preset_type):
    """重置指定类型的工作流预设到初始值"""
    from hengline.utils.config_utils import reset_workflow_preset
    
    # 验证预设类型
    valid_types = ['text_to_image', 'image_to_image', 'text_to_video', 'image_to_video']
    if preset_type not in valid_types:
        flash('无效的预设类型', 'error')
        return redirect(url_for('config.configure'))
    
    # 重置预设
    reset_workflow_preset(preset_type)
    
    # 提示成功
    flash(f"{preset_type.replace('_', ' ')}配置已恢复到初始值！", 'success')
    return redirect(url_for('config.configure'))
