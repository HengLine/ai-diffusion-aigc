import re
from datetime import datetime

class MedicalTools:
    # 预编译正则表达式以提高性能
    _symptom_regex = None
    _inappropriate_regex = None
    
    # 静态初始化，只执行一次
    if _symptom_regex is None:
        # 症状模式映射表
        symptom_map = {
            '发热': ['发热', '发烧'],
            '咳嗽': ['咳嗽'],
            '头痛': ['头痛'],
            '乏力': ['乏力', '疲劳'],
            '恶心': ['恶心', '呕吐'],
            '腹泻': ['腹泻'],
            '腹痛': ['腹痛'],
            '胸痛': ['胸痛'],
            '呼吸困难': ['呼吸困难'],
            '头晕': ['头晕'],
            '关节痛': ['关节痛'],
            '肌肉痛': ['肌肉痛'],
            '喉咙痛': ['喉咙痛'],
            '鼻塞': ['鼻塞', '流鼻涕'],
            '皮疹': ['皮疹'],
            '出血': ['出血']
        }
        
        # 预编译症状正则表达式
        symptom_patterns = '|'.join(['|'.join(v) for v in symptom_map.values()])
        _symptom_regex = re.compile(symptom_patterns)
        
        # 预编译不适当问题的正则表达式
        inappropriate_patterns = '|'.join([
            '安乐死', '自杀', '毒品', '违禁药物',
            '堕胎', '非法医疗', '如何自制药物'
        ])
        _inappropriate_regex = re.compile(inappropriate_patterns)
    
    @staticmethod
    def extract_symptoms(text):
        """从文本中提取症状信息 - 优化版"""
        if not text:
            return []
        
        # 使用预编译的正则表达式和集合去重
        symptoms = set()
        matches = MedicalTools._symptom_regex.findall(text)
        
        # 将匹配的症状映射到标准名称
        for match in matches:
            for standard_name, variants in MedicalTools.symptom_map.items():
                if match in variants:
                    symptoms.add(standard_name)
                    break
        
        return list(symptoms)
    
    @staticmethod
    def assess_severity(symptoms):
        """评估症状严重程度 - 优化版"""
        if not symptoms:
            return "无明显症状"
        
        # 转换为集合以加速查找
        symptom_set = set(symptoms)
        
        # 严重症状集合
        severe_symptoms = {'胸痛', '呼吸困难', '严重出血', '意识丧失', '高热(>40℃)'}
        
        # 中等严重症状集合
        moderate_symptoms = {'持续高热(38.5-40℃)', '剧烈头痛', '严重呕吐', '严重腹泻'}
        
        # 使用集合交集快速判断
        if severe_symptoms.intersection(symptom_set):
            return "严重：建议立即就医"
        elif moderate_symptoms.intersection(symptom_set):
            return "中等：建议尽快就医"
        
        return "轻微：可以先观察，如症状加重请及时就医"
    
    @staticmethod
    def format_medical_response(answer, sources=None):
        """格式化医疗回答 - 简化版以提高速度"""
        # 仅保留必要的免责声明，移除时间戳以减少处理
        disclaimer = "\n\n【免责声明】：本回答仅供参考，不构成医疗建议。"
        
        formatted_answer = answer + disclaimer
        
        if sources:
            formatted_answer += f"\n参考来源：{sources}"
        
        return formatted_answer
    
    @staticmethod
    def validate_medical_query(query):
        """验证医疗查询是否合适 - 使用预编译正则加速"""
        if not query:
            return True, None
        
        # 使用预编译的正则表达式进行快速匹配
        if MedicalTools._inappropriate_regex.search(query):
            return False, "抱歉，我无法回答这个问题。"
        
        return True, None