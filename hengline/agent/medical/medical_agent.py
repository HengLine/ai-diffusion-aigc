import os
import sys
import glob
import os
import warnings

from langchain_core._api import LangChainDeprecationWarning
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)

from langchain.agents import initialize_agent, Tool
from langchain.chains import RetrievalQA
# 按照最新的langchain导入规范，从langchain_community导入组件
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.tools import DuckDuckGoSearchRun

# 添加项目根目录到Python路径，以便导入tools模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
# 导入医疗专用工具
from tools.medical_tools import MedicalTools

class MedicalAgent:
    def __init__(self):
        # 初始化语言模型 - 使用Ollama并优化参数以提高响应速度
        self.llm = ChatOllama(
            model="gemma3:4b",  # Ollama中的模型名称，使用更通用的llama3
            temperature=0,
            base_url="http://localhost:11434",  # Ollama默认API地址
            # 增加超时时间以解决连接问题
            timeout=300,
            # 移除JSON格式要求，某些模型可能不支持
            # format="json"
        )
        
        # 加载RAG数据
        self.vectorstore = self.load_medical_knowledge()
        
        # 创建检索链 - 减少检索文档数量以提高速度
        self.retrieval_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 2}  # 从3减少到2，减少需要处理的文档数量
            ),
            return_source_documents=True
        )
        
        # 创建网络搜索工具
        self.search = DuckDuckGoSearchRun()
        
        # 定义工具列表
        self.tools = [
            Tool(
                name="Medical Knowledge Base",
                func=self.query_medical_knowledge,
                description="适合用来回答医学知识相关的问题，包括疾病、药物、急救和健康生活方式等内容"
            ),
            Tool(
                name="Web Search",
                func=self.search.run,
                description="适合用来搜索最新的医疗信息、研究进展和新闻等互联网信息"
            ),
            Tool(
                name="Symptom Extractor",
                func=self.extract_symptoms,
                description="适合用来从文本中提取症状信息"
            ),
            Tool(
                name="Severity Assessment",
                func=self.assess_severity,
                description="适合用来评估症状的严重程度"
            )
        ]
        
        # 初始化智能体 - 关闭verbose输出以提高响应速度
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent="zero-shot-react-description",
            verbose=False,  # 从True改为False，减少输出信息
            handle_parsing_errors=True,
            max_iterations=3,  # 限制最大迭代次数
            early_stopping_method="force"
        )
        
        # 初始化医疗工具
        self.medical_tools = MedicalTools()
    
    def load_medical_knowledge(self):
        """加载医疗知识库数据"""
        # 获取data目录下的所有txt文件
        data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../../data")
        files = glob.glob(os.path.join(data_dir, "*.txt"))
        
        if not files:
            print("警告: 未找到医疗知识库文件。将创建一个空的向量存储。")
            from langchain_community.embeddings import FakeEmbeddings
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
        print("使用FakeEmbeddings创建向量存储...")
        from langchain_community.embeddings import FakeEmbeddings
        vectorstore = Chroma.from_documents(texts, FakeEmbeddings(size=768))
        
        return vectorstore
    
    def query_medical_knowledge(self, query):
        """查询医疗知识库 - 优化查询逻辑以提高响应速度"""
        try:
            # 快速查询
            result = self.retrieval_chain.invoke(query)
            
            # 格式化回答，包含来源信息
            answer = result["result"]
            
            # 简化处理逻辑，减少不必要的操作
            sources = set()
            for doc in result["source_documents"]:
                if "source" in doc.metadata:
                    sources.add(os.path.basename(doc.metadata["source"]))
            
            formatted_sources = "\n来源: " + ", ".join(sources) if sources else ""
            
            # 直接返回回答，减少额外处理
            return f"{answer}{formatted_sources}"
        except Exception as e:
            print(f"知识库查询错误: {e}")
            return f"知识库查询失败: {str(e)}"
        
    def extract_symptoms(self, text):
        """提取症状信息"""
        symptoms = self.medical_tools.extract_symptoms(text)
        if symptoms:
            return f"提取到的症状: {', '.join(symptoms)}"
        else:
            return "未提取到明显症状"
            
    def assess_severity(self, symptoms_text):
        """评估症状严重程度"""
        # 先从文本中提取症状
        symptoms = self.medical_tools.extract_symptoms(symptoms_text)
        if not symptoms:
            return "未提取到可评估的症状"
        
        # 评估严重程度
        severity = self.medical_tools.assess_severity(symptoms)
        return f"症状: {', '.join(symptoms)}\n{severity}"
    
    def run(self, question):
        """运行智能体回答问题"""
        # 验证医疗查询是否合适
        is_valid, error_msg = self.medical_tools.validate_medical_query(question)
        if not is_valid:
            return error_msg
        
        # 使用invoke方法替代已过时的run方法
        return self.agent.invoke(question)

if __name__ == "__main__":
    # 创建医疗智能体实例
    medical_agent = MedicalAgent()
    
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
    for q in questions:
        print(f"\n问题: {q}")
        result = medical_agent.run(q)
        print(f"回答: {result}")