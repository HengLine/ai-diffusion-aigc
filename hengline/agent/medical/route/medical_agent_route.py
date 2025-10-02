from flask import Blueprint, render_template, request, jsonify
import time

from hengline.logger import debug, error, warning, info
from hengline.agent.medical.api.medical_api_client import get_medical_api_client

# 创建蓝图
medical_agent_bp = Blueprint('medical_agent', __name__)

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
        
        # 调用医疗问答API客户端
        response = get_medical_api_client().query_medical_question(question)
        # response = get_medical_api_client().generate_medical_answer(question)
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '医疗问答任务已开始处理',
            'data': {
                'question': question,
                'answer': response['answer'],
                'agent_type': 'medical'
            }
        })
        
    except Exception as e:
        error(f"医疗问答Agent处理错误: {str(e)}")
        return jsonify({'success': False, 'message': f'处理请求时发生错误: {str(e)}'}), 500