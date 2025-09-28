import logging
from flask import Blueprint, render_template, request, jsonify
from hengline.agent.config.llm_config import get_llm_config, save_llm_config

# 创建蓝图
agent_config_bp = Blueprint('agent_config', __name__)

# 配置日志
logger = logging.getLogger(__name__)


@agent_config_bp.route('/agent/config', methods=['GET'])
def agent_config_page():
    """
    智能体配置页面路由
    """
    try:
        # 获取当前LLM配置
        llm_config = get_llm_config()
        return render_template('agent/agent_config.html', llm_config=llm_config)
    except Exception as e:
        logger.error(f"加载智能体配置页面失败: {str(e)}")
        return render_template('agent/agent_config.html', llm_config={})


@agent_config_bp.route('/api/agent/config', methods=['GET'])
def get_llm_config_api():
    """
    获取LLM配置的API接口
    """
    try:
        llm_config = get_llm_config()

        return jsonify({
            'success': True,
            'data': llm_config
        })
    except Exception as e:
        logger.error(f"获取LLM配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取配置失败: {str(e)}'
        }), 500


@agent_config_bp.route('/api/agent/config', methods=['POST'])
def save_llm_config_api():
    """
    保存LLM配置的API接口
    """
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '无效的请求数据'
            }), 400
        
        # 保存配置
        result = save_llm_config(**data)
        
        if result:
            return jsonify({
                'success': True,
                'message': '配置保存成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '配置保存失败'
            }), 500
    except Exception as e:
        logger.error(f"保存LLM配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'保存配置时发生错误: {str(e)}'
        }), 500