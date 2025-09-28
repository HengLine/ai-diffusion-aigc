import os
import json
import os

from hengline.logger import error, debug
from hengline.utils.config_utils import reload_config


def _get_agent_config_path():
    """获取智能体配置文件路径"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(project_root, 'configs', 'ageny_config.json')

def load_agent_config():
    """加载智能体配置文件"""
    config_path = _get_agent_config_path()
    try:
        if not os.path.exists(config_path):
            # 如果文件不存在，创建默认配置文件
            default_config = {
                "settings": {
                    "llm_provider": "ollama",
                    "llm_config": {
                        "openai": {
                            "api_key": "",
                            "api_url": "https://api.openai.com/v1",
                            "models": "gpt-4o"
                        },
                        "anthropic": {
                            "api_key": "",
                            "api_url": "https://api.anthropic.com/v1",
                            "models": "claude-3-opus"
                        },
                        "zhipu": {
                            "api_key": "",
                            "api_url": "https://open.bigmodel.cn/api/paas/v4",
                            "models": "glm-4"
                        },
                        "qwen": {
                            "api_key": "",
                            "api_url": "https://openai.api.qcloud.com/v2",
                            "models": "qwen-3.5"
                        },
                        "vllm": {
                            "api_key": "",
                            "api_url": "http://localhost:8000/v1",
                            "models": "qwen3"
                        },
                        "ollama": {
                            "api_key": "",
                            "api_url": "http://localhost:11434/api",
                            "models": "llama3"
                        },
                        "custom": {
                            "api_key": "",
                            "api_url": "",
                            "models": ""
                        }
                    }
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            return default_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            debug(f"成功加载智能体配置文件: {config_path}")
            return config
    except Exception as e:
        error(f"加载智能体配置文件失败: {str(e)}")
        # 返回默认配置
        return {
            "settings": {
                "llm_provider": "openai",
                "llm_config": {
                    "openai": {
                        "api_key": "",
                        "api_url": "https://api.openai.com/v1",
                        "models": "gpt-4o"
                    }
                }
            }
        }

def get_llm_config():
    """获取LLM配置，转换为前端所需的格式
    
    Returns:
        dict: LLM配置信息
    """
    try:
        config = load_agent_config()
        # 确保settings和llm_config节点存在
        if 'settings' not in config:
            config['settings'] = {
                'llm_provider': 'openai',
                'llm_config': {
                    'openai': {
                        'api_key': '',
                        'api_url': 'https://api.openai.com/v1',
                        'models': 'gpt-4o'
                    }
                }
            }
        
        if 'llm_config' not in config['settings']:
            config['settings']['llm_config'] = {
                'openai': {
                    'api_key': '',
                    'api_url': 'https://api.openai.com/v1',
                    'models': 'gpt-4o'
                }
            }
        
        # 获取当前选择的提供商
        selected_provider = config['settings'].get('llm_provider', 'openai')
        llm_config_data = config['settings']['llm_config']
        
        # 转换为前端所需的格式
        result = {
            'selected_provider': selected_provider,
            'default_model': llm_config_data.get(selected_provider, {}).get('models', 'gpt-4o')
        }
        
        # 为每个提供商添加对应的配置项
        for provider in llm_config_data:
            provider_data = llm_config_data[provider]
            result[f'{provider}_api_key'] = provider_data.get('api_key', '')
            result[f'{provider}_base_url'] = provider_data.get('api_url', '')
            result[f'{provider}_model'] = provider_data.get('models', '')
        
        # 确保所有必需的字段都存在
        default_providers = ['openai', 'anthropic', 'zhipu', 'qwen', 'vllm', 'ollama', 'custom']
        for provider in default_providers:
            if f'{provider}_api_key' not in result:
                result[f'{provider}_api_key'] = ''
            elif result[f'{provider}_api_key'] and result[f'{provider}_api_key'] != '':
                result[f'{provider}_api_key'] = '***************'
            if f'{provider}_base_url' not in result:
                result[f'{provider}_base_url'] = ''
            if f'{provider}_model' not in result:
                result[f'{provider}_model'] = ''
        
        return result
    except Exception as e:
        error(f"获取LLM配置失败: {str(e)}")
        # 返回默认配置
        return {
            'selected_provider': 'openai',
            'default_model': 'gpt-4o',
            'openai_api_key': '',
            'openai_base_url': 'https://api.openai.com/v1',
            'openai_model': 'gpt-4o',
            'anthropic_api_key': '',
            'anthropic_base_url': 'https://api.anthropic.com/v1',
            'anthropic_model': 'claude-3-opus',
            'zhipu_api_key': '',
            'zhipu_base_url': 'https://open.bigmodel.cn/api/paas/v4',
            'zhipu_model': 'glm-4',
            'qwen_api_key': '',
            'qwen_base_url': 'https://openai.api.qcloud.com/v2',
            'qwen_model': 'qwen-3.5',
            'vllm_api_key': '',
            'vllm_base_url': 'http://localhost:8000/v1',
            'vllm_model': 'qwen3',
            'ollama_api_key': '',
            'ollama_base_url': 'http://localhost:11434/api',
            'ollama_model': 'llama3',
            'custom_api_key': '',
            'custom_base_url': '',
            'custom_model': ''
        }


def save_llm_config(**kwargs):
    """保存LLM配置
    
    Args:
        **kwargs: 要保存的LLM配置项
        
    Returns:
        bool: 保存是否成功
    """
    try:
        config_path = _get_agent_config_path()
        config = load_agent_config()

        # 确保settings和llm_config节点存在
        if 'settings' not in config:
            config['settings'] = {'llm_provider': 'openai', 'llm_config': {}}
        
        if 'llm_config' not in config['settings']:
            config['settings']['llm_config'] = {}
        
        llm_config = config['settings']['llm_config']
        
        # 更新选择的提供商
        if 'selected_provider' in kwargs:
            config['settings']['llm_provider'] = kwargs['selected_provider']
        
        # 提供商列表
        providers = ['openai', 'anthropic', 'zhipu', 'qwen', 'vllm', 'ollama', 'custom']
        
        # 更新每个提供商的配置
        for provider in providers:
            if provider not in llm_config:
                llm_config[provider] = {'api_key': '', 'api_url': '', 'models': ''}
            
            # 更新API密钥
            if f'{provider}_api_key' in kwargs:
                api_key = kwargs[f'{provider}_api_key']
                if api_key and api_key != '***************':
                    llm_config[provider]['api_key'] = api_key
            
            # 更新基础URL
            if f'{provider}_base_url' in kwargs:
                llm_config[provider]['api_url'] = kwargs[f'{provider}_base_url']
            
            # 更新模型
            if f'{provider}_model' in kwargs:
                llm_config[provider]['models'] = kwargs[f'{provider}_model']
        
        # 写回文件
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 重新加载配置
        reload_config()
        debug(f"成功保存LLM配置")
        return True
    except Exception as e:
        error(f"保存LLM配置失败: {str(e)}")
        return False


def get_selected_llm_provider():
    """获取当前选择的LLM提供商
    
    Returns:
        str: LLM提供商名称
    """
    config = load_agent_config()
    return config.get('settings', {}).get('llm_provider', 'openai')


def get_default_model():
    """获取默认模型
    
    Returns:
        str: 默认模型名称
    """
    config = load_agent_config()
    selected_provider = config.get('settings', {}).get('llm_provider', 'openai')
    llm_config = config.get('settings', {}).get('llm_config', {})
    return llm_config.get(selected_provider, {}).get('models', 'gpt-4o')


def get_provider_config(provider):
    """获取指定提供商的配置
    
    Args:
        provider (str): 提供商名称
        
    Returns:
        dict: 提供商配置
    """
    config = load_agent_config()
    llm_config = config.get('settings', {}).get('llm_config', {})
    provider_data = llm_config.get(provider, {})
    return {
        'api_key': provider_data.get('api_key', ''),
        'base_url': provider_data.get('api_url', '')
    }


def get_all_llm_providers():
    """获取所有LLM提供商列表
    
    Returns:
        list: 提供商名称列表
    """
    config = load_agent_config()
    llm_config = config.get('settings', {}).get('llm_config', {})
    return list(llm_config.keys())