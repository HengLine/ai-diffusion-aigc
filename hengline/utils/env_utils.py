import os
from dotenv import load_dotenv

# 全局变量，标记是否已加载.env文件
_is_env_loaded = False

def load_env_file(env_file_path=None):
    """
    加载.env文件中的环境变量
    
    Args:
        env_file_path: .env文件的路径，如果为None则使用当前目录下的.env文件
    """
    global _is_env_loaded
    
    if _is_env_loaded:
        return
    
    # 默认使用项目根目录下的.env文件
    if env_file_path is None:
        # 计算.env文件的路径：从当前文件向上三层目录
        current_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        env_file_path = os.path.join(project_root, '.env')
    
    # 尝试加载.env文件
    if os.path.exists(env_file_path):
        load_dotenv(env_file_path)
        _is_env_loaded = True
    

def get_env_var(name, default=None):
    """
    获取环境变量的值
    
    Args:
        name: 环境变量的名称
        default: 如果环境变量不存在，返回的默认值
    
    Returns:
        str: 环境变量的值，如果不存在则返回默认值
    """
    # 确保.env文件已加载
    if not _is_env_loaded:
        load_env_file()
    
    return os.environ.get(name, default)