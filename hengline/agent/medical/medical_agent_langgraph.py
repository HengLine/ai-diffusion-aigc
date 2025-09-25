import sys
import glob
import os
from typing import List, Tuple, Any, Dict

from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings, FakeEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# 添加项目根目录到Python路径，以便导入tools模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
# 导入医疗专用工具
from tools.medical_tools import MedicalTools

# LangGraph相关导入
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

class MedicalAgentState:
    """定义智能体的状态结构"""
    messages: List[BaseMessage] = add_messages()
    # 可以添加其他状态字段，如思考过程、使用的工具等

class MedicalAgentLangGraph:
    def __init__(self):
        # 初始化语言模型 - 使用Ollama并优化参数以提高响应速度
        # 尝试使用支持工具调用的模型
        try:
            self.llm = ChatOllama(
                model="llama3.2",  # 使用更通用的llama3模型，假设它支持工具调用
                temperature=0,
                base_url="http://localhost:11434",  # Ollama默认API地址
                # 增加超时时间以解决连接问题
                timeout=300
            )
            self.model_supports_tools = True
        except Exception as e:
            # 如果llama3不可用，尝试使用其他可能的模型
            print(f"尝试使用llama3模型失败: {str(e)}")
            self.llm = ChatOllama(
                model="qwen3",  # 使用mistral作为备选
                temperature=0,
                base_url="http://localhost:11434",
                timeout=300
            )
            self.model_supports_tools = False
            print("已切换到不支持工具调用的模型，将使用简化的回答模式")
        
        # 导入医疗工具
        self.medical_tools = MedicalTools()
        
        # 加载RAG数据
        self.vectorstore = self.load_medical_knowledge()
        
        # 创建检索链 - 减少检索文档数量以提高速度
        self.retrieval_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 2}  # 减少需要处理的文档数量
            ),
            return_source_documents=True
        )
        
        # 创建网络搜索工具
        self.search = DuckDuckGoSearchRun()
        
        # 定义工具列表
        self.tools = [
            self.query_medical_knowledge_tool,
            self.web_search_tool,
            self.extract_symptoms_tool,
            self.assess_severity_tool
        ]
        
        # 初始化LangGraph智能体
        self.agent = self._initialize_langgraph_agent()
    
    @tool
    def query_medical_knowledge_tool(self, query: str) -> str:
        """适合用来回答医学知识相关的问题，包括疾病、药物、急救和健康生活方式等内容"""
        return self.query_medical_knowledge(query)
    
    @tool
    def web_search_tool(self, query: str) -> str:
        """适合用来搜索最新的医疗信息、研究进展和新闻等互联网信息"""
        return self.search.run(query)
    
    @tool
    def extract_symptoms_tool(self, text: str) -> List[str]:
        """适合用来从文本中提取症状信息"""
        return self.extract_symptoms(text)
    
    @tool
    def assess_severity_tool(self, symptoms: List[str]) -> str:
        """适合用来评估症状的严重程度"""
        return self.assess_severity(symptoms)
    
    def _initialize_langgraph_agent(self):
        """初始化LangGraph智能体"""
        # 创建React Agent - 简化配置，不使用checkpointer以避免配置错误
        agent_executor = create_react_agent(
            self.llm,
            self.tools
        )
        return agent_executor
    
    def load_medical_knowledge(self):
        """加载医疗知识库数据"""
        # 获取data目录下的所有txt文件
        data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../../data")
        files = glob.glob(os.path.join(data_dir, "*.txt"))
        
        if not files:
            print("警告: 未找到医疗知识库文件。将创建一个空的向量存储。")
            from langchain_core.documents import Document
            # 创建空文档列表并使用from_documents方法初始化Chroma
            empty_docs = [Document(page_content="这是一个空的医疗知识库文档", metadata={"source": "empty"})]
            return Chroma.from_documents(empty_docs, FakeEmbeddings(size=768))
        
        # 加载文档
        documents = []
        for file in files:
            loader = TextLoader(file, encoding="utf-8")
            documents.extend(loader.load())
        
        # 分割文档
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        
        # 创建向量存储 - 使用FakeEmbeddings避免下载外部模型
        # print("使用FakeEmbeddings创建向量存储...")
        vectorstore = Chroma.from_documents(texts, FakeEmbeddings(size=768))
        
        return vectorstore
    
    def query_medical_knowledge(self, query):
        """查询医疗知识库"""
        try:
            # 快速查询
            result = self.retrieval_chain.invoke(query)
            
            # 提取回答和来源
            answer = result["result"]
            sources = [doc.metadata["source"] for doc in result.get("source_documents", [])]
            
            # 返回格式化的回答
            if sources:
                return f"{answer}\n\n信息来源: {', '.join(sources)}"
            return answer
        except Exception as e:
            return f"查询知识库时出错: {str(e)}"
    
    def extract_symptoms(self, text):
        """从文本中提取症状信息"""
        return self.medical_tools.extract_symptoms(text)
    
    def assess_severity(self, symptoms):
        """评估症状的严重程度"""
        return self.medical_tools.assess_severity(symptoms)
    
    def run(self, question):
        """运行智能体回答问题"""
        # 验证医疗查询是否合适
        is_valid, error_msg = self.medical_tools.validate_medical_query(question)
        if not is_valid:
            return error_msg
        
        try:
            # 尝试使用LangGraph智能体处理问题
            result = self.agent.invoke({
                "messages": [HumanMessage(content=question)]
            })
            
            # 从结果中提取回答
            if isinstance(result, dict) and "messages" in result:
                for message in reversed(result["messages"]):
                    if isinstance(message, AIMessage):
                        return message.content
            
            return str(result)
        except Exception as e:
            # 捕获工具调用相关的错误
            if "does not support tools" in str(e) or not self.model_supports_tools:
                print("模型不支持工具调用，使用简化模式回答")
                # 直接使用语言模型回答，不使用工具
                response = self.llm.invoke([HumanMessage(content=question)])
                return response.content
            else:
                # 其他错误
                return f"处理问题时出错: {str(e)}"

if __name__ == "__main__":
    # 创建基于LangGraph的医疗智能体实例
    medical_agent = MedicalAgentLangGraph()
    
    # 示例问题
    questions = [
        "什么是高血压？如何预防？",
        "老年高血压患者有哪些注意事项？",
        "脑血栓的高危因素有哪些？如何预防？",
        "糖尿病的预防措施有哪些？",
        "老年人如何保持健康的生活方式？",
        "高血压、糖尿病和脑血栓之间有什么关系？",
        "高危人群应该多久进行一次体检？"
    ]
    
    # 运行示例
    print("基于LangGraph的医疗智能体已启动。输入'退出'或'quit'结束会话。")
    try:
        # 首先运行预设问题
        for q in questions:
            print(f"\n问题: {q}")
            result = medical_agent.run(q)
            print(f"回答: {result}")
            
        # 然后进入交互模式
        print("\n预设问题已完成。现在可以输入您自己的问题：")
        while True:
            user_question = input("\n请输入您的问题: ")
            if user_question.lower() in ['退出', 'quit', 'exit']:
                print("感谢使用医疗智能体，再见！")
                break
            result = medical_agent.run(user_question)
            print(f"回答: {result}")
    except KeyboardInterrupt:
        print("\n程序被用户中断，再见！")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")