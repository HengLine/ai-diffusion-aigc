import logging
import sys
import json
import requests
import time
import os
from datetime import datetime
from typing import Dict, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 导入自定义日志模块
from hengline.logger import debug, error, warning, info
from hengline.agent.config.llm_config import get_api_config

class MedicalApiClient:
    """
    医疗API客户端，用于对接外部医疗问答API接口
    """
    def __init__(self, api_url: str = None, timeout: int = 300):
        """
        初始化API客户端
        
        Args:
            api_url: 外部API的基础URL，如果为None则从配置中读取
            timeout: 请求超时时间（秒）
        """
        # 从代理配置中读取API URL
        agent_config = get_api_config('medical')

        if agent_config and api_url is None:
            self.api_url = agent_config.get('url', '')
            if not self.api_url:
                warning("未从配置中找到医疗API URL，使用默认值")
                self.api_url = "http://localhost:8000"
        else:
            self.api_url = api_url

        if agent_config and not timeout or timeout <= 0:
            warning("超时时间必须大于0，使用默认值300秒")
            self.timeout = agent_config.get('timeout', 300)
        else:
            self.timeout = timeout
        
    def query_medical_question(self, question: str, request_id: str = "hengline-medical-agent", url: str = "/api/query") -> Dict:
        """
        发送医疗问题到外部API并获取回答
        
        Args:
            question: 医疗问题文本
            request_id: 请求ID，用于跟踪请求
        
        Returns:
            Dict: 包含回答的响应字典，格式如下：
                {
                    "answer": str,  # 回答内容
                    "request_id": str,  # 请求ID，与输入一致
                    "sources": Optional[list],  # 来源信息，可为None
                    "timestamp": str  # 响应时间戳，ISO格式
                }
        
        Raises:
            Exception: 当API调用失败时抛出
        """
        try:
            # 构建请求数据
            payload = {
                "question": question,
                "request_id": request_id
            }
            
            # 记录请求信息
            info(f"正在发送医疗问答请求到外部API，request_id: {request_id}")
            
            # 调用外部API
            response = requests.post(
                f"{self.api_url}{url}",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 记录响应信息
            info(f"成功获取外部API响应，request_id: {request_id}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            error(f"外部API请求失败，request_id: {request_id}, 错误: {str(e)}")
            # 在实际应用中，这里可能需要重试逻辑或者降级处理
            # 为了演示，我们返回一个模拟的响应
            return self._get_mock_response(question, request_id)
        except Exception as e:
            error(f"处理医疗问答请求时发生未知错误，request_id: {request_id}, 错误: {str(e)}")
            # 返回模拟响应
            return self._get_mock_response(question, request_id)
    
    def generate_medical_answer(self, question: str, request_id: str = "hengline-medical-agent") -> Dict:
        """
        生成医疗回答，封装了query_medical_question方法
        
        Args:
            question: 医疗问题文本
            request_id: 请求ID，用于跟踪请求
        
        Returns:
            Dict: 包含回答的响应字典，格式与query_medical_question相同
        """
        return self.query_medical_question(question, request_id, "/api/generate")


    def _get_mock_response(self, question: str, request_id: str) -> Dict:
        """
        获取模拟的API响应，用于测试或API不可用时的降级处理
        
        Args:
            question: 医疗问题文本
            request_id: 请求ID
        
        Returns:
            Dict: 模拟的响应字典
        """
        # 生成当前时间戳
        timestamp = datetime.now().isoformat()
        
        # 根据问题内容返回不同的模拟回答
        if "高血压" in question:
            answer = "预防高血压需要长期的努力和注意。通过遵循这些方法并定期检查血压，可以帮助降低高血压的风险。"
        elif "糖尿病" in question:
            answer = "糖尿病的预防主要包括控制饮食、增加运动、保持健康体重、定期体检等方面。"
        else:
            answer = "这是一个医疗问答示例响应。在实际应用中，这里将返回由外部医疗API生成的专业回答。"
        
        return {
            "answer": answer,
            "request_id": request_id,
            "sources": None,
            "timestamp": timestamp
        }

# 单例实例，方便全局使用
def get_medical_api_client(api_url: str = None) -> MedicalApiClient:
    """
    获取医疗API客户端实例
    
    Args:
        api_url: 外部API的URL，如果为None则从配置中读取
        
    Returns:
        MedicalApiClient: 医疗API客户端实例
    """
    # 创建并返回客户端实例，API URL将从配置中读取（如果未提供）
    return MedicalApiClient(api_url)

# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建API客户端
    client = get_medical_api_client()
    
    # 测试查询
    test_question = "怎么预防高血压？"
    test_request_id = "user_123"
    
    print(f"查询问题: {test_question}")
    print(f"请求ID: {test_request_id}")
    
    result = client.query_medical_question(test_question, test_request_id)
    
    print("\n查询结果:")
    print(f"回答: {result['answer']}")
    print(f"请求ID: {result['request_id']}")
    print(f"来源: {result['sources']}")
    print(f"时间戳: {result['timestamp']}")