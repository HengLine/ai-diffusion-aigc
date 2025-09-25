from flask import Blueprint, render_template, request, jsonify
import logging
import time

# 创建蓝图
medical_agent_bp = Blueprint('medical_agent', __name__)

# 配置日志
logger = logging.getLogger(__name__)

@medical_agent_bp.route('/agent/medical', methods=['GET'])
def medical_agent_page():
    """
    医疗问答Agent页面路由
    """
    return render_template('agent/medical_agent.html')

@medical_agent_bp.route('/api/medical_agent', methods=['POST'])
def api_medical_agent():
    """
    医疗问答Agent API接口
    """
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        # 获取必要的参数
        question = data.get('question')
        if not question or not question.strip():
            return jsonify({'success': False, 'message': '请输入您的医疗问题'}), 400
        
        # 模拟处理时间
        time.sleep(1)
        
        # 这里应该是实际调用医疗问答Agent的代码
        # 由于是示例，我们返回一个模拟的响应
        # 实际项目中应该调用真实的医疗问答模型或API
        
        # 检查是否需要排队（示例逻辑）
        # 这里假设当前没有排队，直接处理
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '医疗问答任务已开始处理',
            'data': {
                'question': question,
                'answer': '这是一个医疗问答示例响应。在实际应用中，这里将返回由医疗AI生成的专业回答。',
                'agent_type': 'medical'
            }
        })
        
    except Exception as e:
        logger.error(f"医疗问答Agent处理错误: {str(e)}")
        return jsonify({'success': False, 'message': f'处理请求时发生错误: {str(e)}'}), 500