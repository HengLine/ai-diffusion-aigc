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
    return get_config_section('comfyui', {
        'api_url': 'http://127.0.0.1:8188',
        'auto_start_server': False
    })


def get_comfyui_api_url():
    """获取ComfyUI的API URL"""
    return get_comfyui_config().get('api_url', 'http://127.0.0.1:8188')


def get_user_configs():
    """获取用户信息"""
    return get_config_section('user', {
        'email': '',
        'nickname': '',
        'avatar': 'default_avatar.png',
        'preferred_language': 'zh-CN',
        'organization': ''
    })

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
            'presets': {
                'text_to_image': {
                    'default': {
                        'model': 'v1-5-pruned-emaonly.safetensors',
                        'vae': 'vae-ft-mse-840000-ema-pruned.safetensors',
                        'sampler': 'dpmpp_2m_sde_karras',
                        'steps': 20,
                        'cfg': 7.0,
                        'width': 512,
                        'height': 512,
                        'batch_size': 1
                    }
                },
                'image_to_image': {
                    'default': {
                        'model': 'v1-5-pruned-emaonly.safetensors',
                        'vae': 'vae-ft-mse-840000-ema-pruned.safetensors',
                        'sampler': 'dpmpp_2m_sde_karras',
                        'steps': 20,
                        'cfg': 7.0,
                        'denoising_strength': 0.75,
                        'width': 512,
                        'height': 512
                    }
                },
                'image_to_video': {
                    'default': {
                        'model': 'svd.safetensors',
                        'motion_bucket_id': 127,
                        'noise_aug_strength': 0.02,
                        'num_frames': 16,
                        'fps': 8,
                        'decode_chunk_size': 8,
                        'width': 512,
                        'height': 320
                    }
                },
                'text_to_video': {
                    'default': {
                        'model': 'svd.safetensors',
                        'motion_bucket_id': 127,
                        'noise_aug_strength': 0.02,
                        'num_frames': 16,
                        'fps': 8,
                        'decode_chunk_size': 8,
                        'width': 512,
                        'height': 320
                    }
                }
            }
        }

        
def get_workflow_path(task_type):
    """获取指定任务类型的工作流文件路径"""
    return get_workflows_config().get(task_type)


# 初始化加载配置
config = load_config()

# 导出常用配置变量
max_concurrent_tasks = get_max_concurrent_tasks()

