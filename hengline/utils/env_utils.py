import os
from pathlib import Path

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
        # current_dir = os.path.dirname(__file__)
        # project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        project_root = get_root_by_currentfile()
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


def get_root_by_currentfile():
    """通过当前文件路径回溯查找项目根目录"""
    current_path = Path(__file__).absolute()  # 获取当前文件的绝对路径
    while True:
        # 检测根目录标记（可自行修改条件）
        if (current_path / 'requirements.txt').exists() \
                or (current_path / '.git').is_dir():
            return current_path
        # 到达系统根目录时终止
        if current_path == current_path.parent:
            return current_path  # 返回最终有效路径
        current_path = current_path.parent  # 向上一级目录


def print_large_ascii():
    hengline_large = """
                ██╗  ██╗ ███████╗ ███╗   ██╗  ██████╗       ██╗      ██╗ ███╗   ██╗ ███████╗
                ██║  ██║ ██╔════╝ ████╗  ██║ ██╔════╝       ██║      ██║ ████╗  ██║ ██╔════╝
                ███████║ █████╗   ██╔██╗ ██║ ██║  ███╗      ██║      ██║ ██╔██╗ ██║ █████╗  
                ██╔══██║ ██╔══╝   ██║╚██╗██║ ██║   ██║      ██║      ██║ ██║╚██╗██║ ██╔══╝  
                ██║  ██║ ███████╗ ██║ ╚████║ ╚██████╔╝      ███████╗ ██║ ██║ ╚████║ ███████╗
                ╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═══╝  ╚═════╝       ╚══════╝ ╚═╝ ╚═╝  ╚═══╝ ╚══════╝
    """

    aigc_large = """
                                     █████╗     ██╗     ██████╗     ██████╗ 
                                    ██╔══██╗    ╚═╝    ██╔════╝    ██╔════╝ 
                                    ███████║    ██║    ██║  ███╗   ██║      
                                    ██╔══██║    ██║    ██║   ██║   ██║      
                                    ██║  ██║    ██║    ╚██████╔╝   ╚██████╗ 
                                    ╚═╝  ╚═╝    ╚═╝     ╚═════╝     ╚═════╝ 
    """

    print(hengline_large)
    print(aigc_large)


def print_hengline_dots():
    hengline_dots = """
                H   H   EEEEE   N   N   GGGG       L       IIIII   N   N   EEEEE
                H   H   E       NN  N   G          L         I     NN  N   E
                HHHHH   EEEE    N N N   G  GG      L         I     N N N   EEEE
                H   H   E       N  NN   G   G      L         I     N  NN   E
                H   H   EEEEE   N   N   GGGG       LLLLL   IIIII   N   N   EEEEE
    """
    print(hengline_dots)
