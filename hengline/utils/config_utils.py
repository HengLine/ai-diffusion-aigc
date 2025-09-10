# 直接在本文件中加载配置以避免循环导入
import os
import json

# 加载配置文件的简单实现
def _load_config_simple():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        # 如果加载失败，返回默认配置
        return {'settings': {'common': {'max_concurrent_tasks': 2}}}

# 加载配置
config = _load_config_simple()


def get_config_settings():
    return config.get('settings', {})


# 从配置文件获取最大并发任务数，如果没有则使用默认值
max_concurrent_tasks = get_config_settings().get('common', {}).get('max_concurrent_tasks', 2)

