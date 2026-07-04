❌ 未用（按重要程度排序）
│
├── 【高频/重要】
│   ├── OutputParser（输出解析器）
│   │   ├── JsonOutputParser        LLM 输出 → Python dict
│   │   ├── PydanticOutputParser    LLM 输出 → Pydantic 对象
│   │   └── StrOutputParser         提取纯文本内容
│   │
│   ├── .with_structured_output()   强制 LLM 按 schema 输出结构化数据
│   │   # 适合：槽位提取、信息抽取、分类等
│   │
│   ├── LCEL 高级组件
│   │   ├── RunnableParallel        多个 chain 并行执行
│   │   ├── RunnablePassthrough     原样透传输入值
│   │   └── RunnableLambda          把普通函数包装成 Runnable
│   │
│   └── BaseCallbackHandler         LangChain 原生回调（你用的是自定义 Queue）
│
├── 【RAG 相关】
│   ├── Document / DocumentLoader   加载文档
│   ├── TextSplitter                文档分块
│   ├── Embeddings                  文本向量化
│   ├── VectorStore                 向量数据库（FAISS/Chroma等）
│   └── Retriever                   检索器，RAG 的核心
│
└── 【Agent 相关（LangChain 原生）】
    ├── @tool 装饰器                 定义 LangChain 原生工具
    ├── create_react_agent          ReAct 推理框架
    ├── create_openai_tools_agent   Function Calling 框架
    └── AgentExecutor               自动循环调用工具