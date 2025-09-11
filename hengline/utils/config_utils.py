# 配置工具模块，统一管理配置获取
import os
import json
from hengline.logger import info, error, warning

# 全局配置变量
_config = None


def _get_config_path():
    """获取配置文件路径"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'config.json')


def load_config():
    """加载配置文件的主函数"""
    global _config
    if _config is not None:
        return _config
    
    config_path = _get_config_path()
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _config = json.load(f)
            info(f"成功加载配置文件: {config_path}")
            return _config
    except Exception as e:
        error(f"加载配置文件失败: {str(e)}")
        # 如果加载失败，返回默认配置
        _config = {
            'flask': {
                'secret_key': 'default-fallback-key',
                'debug': False,
                'allowed_extensions': ['png', 'jpg', 'jpeg', 'gif']
            },
            'paths': {
                'temp_folder': 'uploads',
                'output_folder': 'outputs',
                'workflows_dir': 'workflows'
            },
            'comfyui': {
                'api_url': 'http://127.0.0.1:8188',
                'auto_start_server': False
            },
            'settings': {
                'common': {
                    'max_concurrent_tasks': 2,
                    'cache_enabled': True,
                    'cache_size': 1024
                }
            }
        }
        return _config


# 重新加载配置（用于配置更新后）
def reload_config():
    """重新加载配置文件"""
    global _config
    _config = None
    return load_config()


# 基础配置获取函数
def get_config():
    """获取完整配置"""
    return load_config()


def get_config_section(section_name, default=None):
    """获取指定配置部分"""
    if default is None:
        default = {}
    return load_config().get(section_name, default)


# Flask 相关配置
def get_flask_config():
    """获取Flask相关配置"""
    return get_config_section('flask', {
        'secret_key': 'default-fallback-key',
        'debug': False,
        'allowed_extensions': ['png', 'jpg', 'jpeg', 'gif']
    })


def get_flask_secret_key():
    """获取Flask的secret_key"""
    return get_flask_config().get('secret_key', 'default-fallback-key')


def get_flask_debug():
    """获取Flask的debug设置"""
    return get_flask_config().get('debug', False)


def get_allowed_extensions():
    """获取允许上传的文件类型"""
    return set(get_flask_config().get('allowed_extensions', ['png', 'jpg', 'jpeg', 'gif']))


# 路径相关配置
def get_paths_config():
    """获取路径相关配置"""
    return get_config_section('paths', {
        'temp_folder': 'uploads',
        'output_folder': 'outputs',
        'workflows_dir': 'workflows'
    })


def get_temp_folder():
    """获取临时文件夹路径"""
    return get_paths_config().get('temp_folder', 'uploads')


def get_output_folder():
    """获取输出文件夹路径"""
    return get_paths_config().get('output_folder', 'outputs')


def get_workflows_dir():
    """获取工作流文件夹路径"""
    return get_paths_config().get('workflows_dir', 'workflows')


# ComfyUI 相关配置
def get_comfyui_config():
    """获取ComfyUI相关配置"""
    # 获取settings.comfyui配置，考虑到配置结构变更
    settings = get_config_section('settings', {})
    return settings.get('comfyui', {
        'api_url': 'http://127.0.0.1:8188',
        'auto_start_server': False
    })


def get_comfyui_api_url():
    """获取ComfyUI的API URL"""
    return get_comfyui_config().get('api_url', 'http://127.0.0.1:8188')


def get_user_configs():
    """获取用户信息"""
    # 获取settings.user配置，考虑到配置结构变更
    settings = get_config_section('settings', {})
    return settings.get('user', {
        'email': '',
        'nickname': '',
        'avatar': 'default_avatar.png',
        'preferred_language': 'zh-CN',
        'organization': ''
    })


def get_settings_config():
    """获取整个settings配置"""
    return get_config_section('settings', {})


def update_settings_config(new_settings):
    """更新整个settings配置"""
    config = load_config()
    config['settings'] = new_settings
    save_config(config)
    return new_settings

# 输出设置
def get_output_config():
    """获取输出设置"""
    return get_config_section('output', {
        'dir': 'outputs',
        'format': {
            'image': 'png',
            'video': 'mp4'
        },
        'quality': {
            'image': 95,
            'video': 25
        }
    })


# 邮件配置
def get_email_config():
    """获取邮件配置"""
    return get_config_section('email', {
        'smtp_server': '',
        'smtp_port': 587,
        'username': '',
        'from_email': '',
        'from_name': ''
    })


# 任务默认设置
def get_settings_config():
    """获取所有任务设置"""
    return get_config_section('settings', {
        'common': {
            'max_concurrent_tasks': 2,
            'cache_enabled': True,
            'cache_size': 1024
        }
    })


def get_common_settings():
    """获取通用设置"""
    return get_settings_config().get('common', {
        'max_concurrent_tasks': 2,
        'cache_enabled': True,
        'cache_size': 1024
    })


def get_task_settings(task_type, default=None):
    """获取指定任务类型的设置"""
    if default is None:
        default = {}
    return get_settings_config().get(task_type, default)


def get_max_concurrent_tasks():
    """获取最大并发任务数"""
    return get_common_settings().get('max_concurrent_tasks', 2)


# 工作流文件路径
def get_workflows_config():
    """获取工作流配置"""
    return get_config_section('workflows', {
        'text_to_image': 'workflows/text_to_image.json',
        'image_to_image': 'workflows/image_to_image.json',
        'image_to_video': 'workflows/text_to_video.json',
        'text_to_video': 'workflows/text_to_video.json'
    })


# 加载工作流预设
def load_workflow_presets():
    """加载工作流预设配置"""
    presets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'workflow_presets.json')
    try:
        with open(presets_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        error(f"加载工作流预设失败: {e}")
        # 返回默认预设
        return {
            'text_to_image': {
                'default': {
                    'width': 512,
                    'height': 512,
                    'steps': 10,
                    'cfg': 6,
                    'prompt': '',
                    'negative_prompt': '',
                    'batch_size': 1,
                    'seed': -1
                },
                'setting': {}
            },
            'image_to_image': {
                'default': {
                    'width': 512,
                    'height': 512,
                    'steps': 10,
                    'cfg': 7.5,
                    'batch_size': 1,
                    'prompt': '',
                    'negative_prompt': '',
                    'seed': -1,
                    'denoising_strength': 0.75
                },
                'setting': {}
            },
            'image_to_video': {
                'default': {
                    'width': 512,
                    'height': 384,
                    'length': 121,
                    'batch_size': 1,
                    'shift': 8,
                    'fps': 16,
                    'prompt': '',
                    'negative_prompt': '',
                    'denoise': 1,
                    'seed': -1,
                    'cfg': 1
                },
                'setting': {}
            },
            'text_to_video': {
                'default': {
                    'width': 576,
                    'height': 320,
                    'length': 121,
                    'fps': 16,
                    'shift': 8,
                    'batch_size': 1,
                    'denoise': 1,
                    'seed': -1,
                    'cfg': 1,
                    'negative_prompt': '',
                    'prompt': ''
                },
                'setting': {}
            }
        }


def get_workflow_preset(task_type, preset_type='setting'):
    """获取指定任务类型的预设配置
    
    Args:
        task_type (str): 任务类型，如'text_to_image', 'image_to_video'等
        preset_type (str): 预设类型，'setting'或'default'
        
    Returns:
        dict: 预设配置
    """
    presets = load_workflow_presets()
    # 如果请求的是setting但为空，则返回default
    if preset_type == 'setting' and not presets.get(task_type, {}).get('setting', {}):
        return presets.get(task_type, {}).get('default', {})
    return presets.get(task_type, {}).get(preset_type, {})


def save_workflow_preset(task_type, config):
    """保存工作流预设配置
    
    Args:
        task_type (str): 任务类型，如'text_to_image', 'image_to_video'等
        config (dict): 要保存的配置
        
    Returns:
        bool: 保存是否成功
    """
    try:
        presets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'workflow_presets.json')
        presets = load_workflow_presets()
        
        # 确保任务类型存在
        if task_type not in presets:
            presets[task_type] = {'default': {}, 'setting': {}}
        
        # 创建配置副本并处理特殊情况
        config_copy = config.copy()
        
        # 对于文生图任务，移除sampler字段
        if task_type == 'text_to_image' and 'sampler' in config_copy:
            del config_copy['sampler']
        
        # 保存到setting节点
        presets[task_type]['setting'] = config_copy
        
        # 写回文件
        with open(presets_path, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        error(f"保存工作流预设失败: {e}")
        return False


def reset_workflow_preset(task_type):
    """重置工作流预设配置（清空setting节点）
    
    Args:
        task_type (str): 任务类型，如'text_to_image', 'image_to_video'等
        
    Returns:
        bool: 重置是否成功
    """
    try:
        presets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'workflow_presets.json')
        presets = load_workflow_presets()
        
        # 确保任务类型存在
        if task_type in presets:
            # 清空setting节点
            presets[task_type]['setting'] = {}
            
            # 写回文件
            with open(presets_path, 'w', encoding='utf-8') as f:
                json.dump(presets, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        error(f"重置工作流预设失败: {e}")
        return False


def get_effective_config(task_type, **kwargs):
    """获取最终的有效配置，遵循优先级：页面输入 > setting节点 > default节点
    
    Args:
        task_type (str): 任务类型
        **kwargs: 页面输入的参数
        
    Returns:
        dict: 最终的有效配置
    """
    # 获取默认配置
    default_config = get_workflow_preset(task_type, 'default')
    # 获取用户设置配置
    setting_config = get_workflow_preset(task_type, 'setting')
    
    # 创建结果配置，先使用默认配置
    result_config = default_config.copy()
    
    # 用用户设置覆盖默认配置
    for key, value in setting_config.items():
        if value is not None and value != '':
            result_config[key] = value
    
    # 用页面输入覆盖前面的配置
    for key, value in kwargs.items():
        if value is not None and value != '':
            result_config[key] = value
    
    return result_config

        
def get_workflow_path(task_type):
    """获取指定任务类型的工作流文件路径"""
    return get_workflows_config().get(task_type)


# 初始化加载配置
config = load_config()

# 导出常用配置变量
max_concurrent_tasks = get_max_concurrent_tasks()

