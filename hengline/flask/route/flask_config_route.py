# -*- coding: utf-8 -*-
"""
配置页面路由模块
负责处理配置页面的显示和提交逻辑
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工作流管理器和配置
from hengline.utils.workflow_utils import workflow_manager, config

# 创建Blueprint
config_bp = Blueprint('config', __name__)

@config_bp.route('/config', methods=['GET', 'POST'])
def configure():
    """配置页面路由"""
    global config
    
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
        
        # 保存用户信息配置
        if 'user' not in config:
            config['user'] = {}
        config['user']['email'] = email
        config['user']['nickname'] = nickname
        config['user']['organization'] = organization
        
        # 保存ComfyUI配置
        if 'comfyui' not in config:
            config['comfyui'] = {}
        config['comfyui']['api_url'] = comfyui_api_url
        
        # 保存模型参数配置
        if 'settings' not in config:
            config['settings'] = {}
        
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
        text_to_video_frames = request.form.get('settings[text_to_video][frames]', '').strip()
        text_to_video_fps = request.form.get('settings[text_to_video][fps]', '').strip()
        text_to_video_cfg = request.form.get('settings[text_to_video][cfg]', '').strip()
        
        if not text_to_video_width or not text_to_video_height or not text_to_video_frames or not text_to_video_fps or not text_to_video_cfg:
            validation_errors.append('文生视频：请填写所有必填字段（宽度、高度、帧数、帧率、CFG值）！')
        
        # 验证图生视频参数
        image_to_video_width = request.form.get('settings[image_to_video][width]', '').strip()
        image_to_video_height = request.form.get('settings[image_to_video][height]', '').strip()
        image_to_video_frames = request.form.get('settings[image_to_video][frames]', '').strip()
        image_to_video_fps = request.form.get('settings[image_to_video][fps]', '').strip()
        image_to_video_cfg = request.form.get('settings[image_to_video][cfg]', '').strip()
        
        if not image_to_video_width or not image_to_video_height or not image_to_video_frames or not image_to_video_fps or not image_to_video_cfg:
            validation_errors.append('图生视频：请填写所有必填字段（宽度、高度、帧数、帧率、CFG值）！')
        
        # 如果有验证错误，显示错误消息并返回
        if validation_errors:
            for error in validation_errors:
                flash(error, 'error')
            return redirect(url_for('config.configure'))
        
        # 处理文生图参数
        if 'text_to_image' not in config['settings']:
            config['settings']['text_to_image'] = {}
        text_to_image_params = config['settings']['text_to_image']
        text_to_image_params['width'] = int(request.form.get('settings[text_to_image][width]', text_to_image_params.get('width', 1024)))
        text_to_image_params['height'] = int(request.form.get('settings[text_to_image][height]', text_to_image_params.get('height', 1024)))
        text_to_image_params['steps'] = int(request.form.get('settings[text_to_image][steps]', text_to_image_params.get('steps', 20)))
        text_to_image_params['cfg'] = float(request.form.get('settings[text_to_image][cfg]', text_to_image_params.get('cfg', 8.0)))
        text_to_image_params['batch_size'] = int(request.form.get('settings[text_to_image][batch_size]', text_to_image_params.get('batch_size', 1)))
        text_to_image_params['seed'] = int(request.form.get('settings[text_to_image][seed]', text_to_image_params.get('seed', -1)))
        text_to_image_params['sampler'] = request.form.get('settings[text_to_image][sampler]', text_to_image_params.get('sampler', 'euler'))
        text_to_image_params['prompt'] = request.form.get('settings[text_to_image][prompt]', text_to_image_params.get('prompt', ''))
        text_to_image_params['negative_prompt'] = request.form.get('settings[text_to_image][negative_prompt]', text_to_image_params.get('negative_prompt', ''))
        
        # 处理图生图参数
        if 'image_to_image' not in config['settings']:
            config['settings']['image_to_image'] = {}
        image_to_image_params = config['settings']['image_to_image']
        image_to_image_params['width'] = int(request.form.get('settings[image_to_image][width]', image_to_image_params.get('width', 1024)))
        image_to_image_params['height'] = int(request.form.get('settings[image_to_image][height]', image_to_image_params.get('height', 1024)))
        image_to_image_params['steps'] = int(request.form.get('settings[image_to_image][steps]', image_to_image_params.get('steps', 20)))
        image_to_image_params['cfg'] = float(request.form.get('settings[image_to_image][cfg]', image_to_image_params.get('cfg', 8.0)))
        image_to_image_params['batch_size'] = int(request.form.get('settings[image_to_image][batch_size]', image_to_image_params.get('batch_size', 1)))
        image_to_image_params['seed'] = int(request.form.get('settings[image_to_image][seed]', image_to_image_params.get('seed', -1)))
        image_to_image_params['denoising_strength'] = float(request.form.get('settings[image_to_image][denoising_strength]', image_to_image_params.get('denoising_strength', 0.7)))
        image_to_image_params['sampler'] = request.form.get('settings[image_to_image][sampler]', image_to_image_params.get('sampler', 'euler'))
        image_to_image_params['prompt'] = request.form.get('settings[image_to_image][prompt]', image_to_image_params.get('prompt', ''))
        image_to_image_params['negative_prompt'] = request.form.get('settings[image_to_image][negative_prompt]', image_to_image_params.get('negative_prompt', ''))
        
        # 处理文生视频参数
        if 'text_to_video' not in config['settings']:
            config['settings']['text_to_video'] = {}
        text_to_video_params = config['settings']['text_to_video']
        text_to_video_params['width'] = int(request.form.get('settings[text_to_video][width]', text_to_video_params.get('width', 576)))
        text_to_video_params['height'] = int(request.form.get('settings[text_to_video][height]', text_to_video_params.get('height', 320)))
        text_to_video_params['frames'] = int(request.form.get('settings[text_to_video][frames]', text_to_video_params.get('frames', 16)))
        text_to_video_params['fps'] = int(request.form.get('settings[text_to_video][fps]', text_to_video_params.get('fps', 8)))
        text_to_video_params['motion_bucket_id'] = int(request.form.get('settings[text_to_video][motion_bucket_id]', text_to_video_params.get('motion_bucket_id', 120)))
        text_to_video_params['noise_aug_strength'] = float(request.form.get('settings[text_to_video][noise_aug_strength]', text_to_video_params.get('noise_aug_strength', 0.02)))
        text_to_video_params['seed'] = int(request.form.get('settings[text_to_video][seed]', text_to_video_params.get('seed', -1)))
        text_to_video_params['cfg'] = float(request.form.get('settings[text_to_video][cfg]', text_to_video_params.get('cfg', 12.0)))
        text_to_video_params['default_prompt'] = request.form.get('settings[text_to_video][default_prompt]', text_to_video_params.get('default_prompt', ''))
        
        # 处理图生视频参数
        if 'image_to_video' not in config['settings']:
            config['settings']['image_to_video'] = {}
        image_to_video_params = config['settings']['image_to_video']
        image_to_video_params['width'] = int(request.form.get('settings[image_to_video][width]', image_to_video_params.get('width', 576)))
        image_to_video_params['height'] = int(request.form.get('settings[image_to_video][height]', image_to_video_params.get('height', 320)))
        image_to_video_params['frames'] = int(request.form.get('settings[image_to_video][frames]', image_to_video_params.get('frames', 16)))
        image_to_video_params['fps'] = int(request.form.get('settings[image_to_video][fps]', image_to_video_params.get('fps', 8)))
        image_to_video_params['motion_bucket_id'] = int(request.form.get('settings[image_to_video][motion_bucket_id]', image_to_video_params.get('motion_bucket_id', 120)))
        image_to_video_params['noise_aug_strength'] = float(request.form.get('settings[image_to_video][noise_aug_strength]', image_to_video_params.get('noise_aug_strength', 0.02)))
        image_to_video_params['seed'] = int(request.form.get('settings[image_to_video][seed]', image_to_video_params.get('seed', -1)))
        image_to_video_params['cfg'] = float(request.form.get('settings[image_to_video][cfg]', image_to_video_params.get('cfg', 12.0)))
        
        # 确保配置目录存在
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'configs')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # 保存配置到文件
        config_path = os.path.join(config_dir, 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # 重新初始化运行器
        workflow_manager.stop_runner()
        
        flash('配置已成功保存！', 'success')
        return redirect(url_for('config.configure'))
    
    # 从配置文件获取当前配置
    comfyui_api_url = config.get('comfyui', {}).get('api_url', 'http://127.0.0.1:8188')
    user_email = config.get('user', {}).get('email', '')
    user_nickname = config.get('user', {}).get('nickname', '')
    user_organization = config.get('user', {}).get('organization', '')
    
    # 获取模型参数配置
    settings = config.get('settings', {})
    
    # 确保所有必需的参数存在
    if 'text_to_image' not in settings:
        settings['text_to_image'] = {
            'width': 1024,
            'height': 1024,
            'steps': 20,
            'cfg': 8.0,
            'batch_size': 1,
            'seed': -1,
            'sampler': 'euler',
            'prompt': '',
            'negative_prompt': ''
        }
    
    if 'image_to_image' not in settings:
        settings['image_to_image'] = {
            'width': 1024,
            'height': 1024,
            'steps': 20,
            'cfg': 8.0,
            'batch_size': 1,
            'seed': -1,
            'denoising_strength': 0.7,
            'sampler': 'euler',
            'prompt': '',
            'negative_prompt': ''
        }
    
    if 'text_to_video' not in settings:
        settings['text_to_video'] = {
            'width': 576,
            'height': 320,
            'frames': 16,
            'fps': 8,
            'motion_bucket_id': 120,
            'noise_aug_strength': 0.02,
            'seed': -1,
            'cfg': 12.0,
            'default_prompt': ''
        }
    
    if 'image_to_video' not in settings:
        settings['image_to_video'] = {
            'width': 576,
            'height': 320,
            'frames': 16,
            'fps': 8,
            'motion_bucket_id': 120,
            'noise_aug_strength': 0.02,
            'seed': -1,
            'cfg': 12.0
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
    global config
    
    if request.method == 'GET':
        # 获取当前配置
        settings = config.get('settings', {})
        
        # 确保所有必需的参数存在
        if 'text_to_image' not in settings:
            settings['text_to_image'] = {
                'width': 1024,
                'height': 1024,
                'steps': 20,
                'cfg': 8.0,
                'batch_size': 1,
                'seed': -1,
                'sampler': 'euler',
                'prompt': '',
                'negative_prompt': ''
            }
        
        if 'image_to_image' not in settings:
            settings['image_to_image'] = {
                'width': 1024,
                'height': 1024,
                'steps': 20,
                'cfg': 8.0,
                'batch_size': 1,
                'seed': -1,
                'denoising_strength': 0.7,
                'sampler': 'euler',
                'prompt': '',
                'negative_prompt': ''
            }
        
        if 'text_to_video' not in settings:
            settings['text_to_video'] = {
                'width': 576,
                'height': 320,
                'frames': 16,
                'fps': 8,
                'motion_bucket_id': 120,
                'noise_aug_strength': 0.02,
                'seed': -1,
                'cfg': 12.0,
                'default_prompt': ''
            }
        
        if 'image_to_video' not in settings:
            settings['image_to_video'] = {
                'width': 576,
                'height': 320,
                'frames': 16,
                'fps': 8,
                'motion_bucket_id': 120,
                'noise_aug_strength': 0.02,
                'seed': -1,
                'cfg': 12.0
            }
            
        return jsonify({
            'success': True,
            'data': {
                'comfyui_api_url': config.get('comfyui', {}).get('api_url', 'http://127.0.0.1:8188'),
                'user_email': config.get('user', {}).get('email', ''),
                'user_nickname': config.get('user', {}).get('nickname', ''),
                'user_organization': config.get('user', {}).get('organization', ''),
                'settings': settings
            }
        })
    
    elif request.method == 'POST':
        # 更新配置
        try:
            data = request.json
            
            # 验证必填字段
            if not data.get('email') or not data.get('nickname') or not data.get('comfyui_api_url'):
                return jsonify({
                    'success': False,
                    'message': '请填写所有必填字段（电子邮箱、用户昵称和ComfyUI API URL）！'
                }), 400
            
            # 保存用户信息配置
            if 'user' not in config:
                config['user'] = {}
            config['user']['email'] = data.get('email', '').strip()
            config['user']['nickname'] = data.get('nickname', '').strip()
            config['user']['organization'] = data.get('organization', '').strip()
            
            # 保存ComfyUI配置
            if 'comfyui' not in config:
                config['comfyui'] = {}
            config['comfyui']['api_url'] = data.get('comfyui_api_url', '').strip()
            
            # 保存模型参数配置
            if 'settings' not in config:
                config['settings'] = {}
            
            # 如果提交了设置数据，则更新
            if data.get('settings'):
                settings_data = data['settings']
                validation_errors = []
                
                # 验证并更新文生图参数
                if settings_data.get('text_to_image'):
                    text_to_image = settings_data['text_to_image']
                    if not text_to_image.get('width') or not text_to_image.get('height') or not text_to_image.get('steps') or text_to_image.get('cfg') is None:
                        validation_errors.append('文生图：请填写所有必填字段（宽度、高度、步数、CFG值）！')
                    
                    if 'text_to_image' not in config['settings']:
                        config['settings']['text_to_image'] = {}
                    config['settings']['text_to_image'].update(text_to_image)
                
                # 验证并更新图生图参数
                if settings_data.get('image_to_image'):
                    image_to_image = settings_data['image_to_image']
                    if not image_to_image.get('width') or not image_to_image.get('height') or not image_to_image.get('steps') or image_to_image.get('cfg') is None:
                        validation_errors.append('图生图：请填写所有必填字段（宽度、高度、步数、CFG值）！')
                    
                    if 'image_to_image' not in config['settings']:
                        config['settings']['image_to_image'] = {}
                    config['settings']['image_to_image'].update(image_to_image)
                
                # 验证并更新文生视频参数
                if settings_data.get('text_to_video'):
                    text_to_video = settings_data['text_to_video']
                    if not text_to_video.get('width') or not text_to_video.get('height') or not text_to_video.get('frames') or not text_to_video.get('fps') or text_to_video.get('cfg') is None:
                        validation_errors.append('文生视频：请填写所有必填字段（宽度、高度、帧数、帧率、CFG值）！')
                    
                    if 'text_to_video' not in config['settings']:
                        config['settings']['text_to_video'] = {}
                    config['settings']['text_to_video'].update(text_to_video)
                
                # 验证并更新图生视频参数
                if settings_data.get('image_to_video'):
                    image_to_video = settings_data['image_to_video']
                    if not image_to_video.get('width') or not image_to_video.get('height') or not image_to_video.get('frames') or not image_to_video.get('fps') or image_to_video.get('cfg') is None:
                        validation_errors.append('图生视频：请填写所有必填字段（宽度、高度、帧数、帧率、CFG值）！')
                    
                    if 'image_to_video' not in config['settings']:
                        config['settings']['image_to_video'] = {}
                    config['settings']['image_to_video'].update(image_to_video)
                
                # 如果有验证错误，返回错误信息
                if validation_errors:
                    return jsonify({
                        'success': False,
                        'message': '\n'.join(validation_errors)
                    }), 400
            
            # 确保配置目录存在
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'configs')
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # 保存配置到文件
            config_path = os.path.join(config_dir, 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 重新初始化运行器
            workflow_manager.stop_runner()
            
            return jsonify({
                'success': True,
                'message': '配置已成功保存！'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'保存配置失败：{str(e)}'
            }), 500