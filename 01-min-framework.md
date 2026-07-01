# 最小集合项目结构

##　划分标准

| 类型 | 含义 |
| -- | -- |
| 框架必须 | |
| 最小业务 | |
| 可裁剪 | |

## 最小集合目录

```tree
项目根/
│
├── startup.py                        # [Core] 启动入口
├── multiprocess_startup.py           # [Core] 多进程生产启动
├── log.py                            # [Core] 日志 + request_id ContextVar
├── utils.py                          # [Core] 通用工具函数
├── requirements.txt                  # [Core] 依赖声明
│
├── configs/                          # [Core] 配置中心
│   ├── __init__.py                   # 导出所有配置常量
│   ├── basic_config.py               # 基础参数（超时、温度、版本号等）
│   ├── model_config.py               # 模型路径与选型
│   ├── server_config.py              # FastAPI 监听地址/端口
│   ├── kb_config.py                  # 知识库（向量库）配置
│   ├── prompt_config.py              # Prompt 基础配置
│   ├── tools_config.py               # 工具开关配置
│   ├── zhfwpt_config.py              # 智慧服务平台连接配置（HIS对接）
│   │
│   ├── tasks.yaml                    # [Core] 主题/任务/槽位/工具 业务地图
│   └── product_function_mapping.txt  # [Core] 产品授权 → 工具名映射
│
├── common/
│   └── exceptions.py                 # [Core] BizException 业务异常
│
├── server/
│   │
│   ├── api.py                        # [Core] FastAPI App 创建 + 路由挂载
│   ├── utils.py                      # [Core] LLM Chain、FastAPI 工具函数
│   ├── zhfwpt_accessor.py            # [Core] HIS/智慧服务平台 HTTP 客户端
│   ├── llm_model_resolver.py         # [Core] LLM 实例解析（按index/名称）
│   ├── sensitive_word_matcher.py     # [Core] 敏感词校验
│   ├── async_task_executor.py        # [Core] 全局异步任务执行器
│   ├── token_estimate.py             # [Core] Token 估算
│   │
│   ├── models/                       # [Core] 核心数据模型
│   │   ├── context_info.py           # 请求上下文（整个链路的核心承载）
│   │   ├── context_engineering_models.py  # ConversationSession/Topic/Task
│   │   ├── request_info.py           # RequestInfo 请求参数封装
│   │   ├── response_result.py        # 响应结构
│   │   ├── constants.py              # 常量（BizCode、配置 key 等）
│   │   ├── range_info.py             # 业务边界对象
│   │   └── request_param_tool_mapping.py  # 请求参数直接映射工具（快捷路由）
│   │
│   ├── callback_handler/             # [Core] 流式回调
│   │   ├── base_stream_callback_handler.py
│   │   ├── stream_callback_handler.py     # 主回调：队列、流控、结果收集
│   │   ├── text_stream_callback_handler.py
│   │   └── conversation_callback_handler.py
│   │
│   ├── cache/                        # [Core] 三级缓存
│   │   ├── cache.py                  # Caches 门面（L1 TTLCache）
│   │   └── hybrid_cache.py           # L1+L2 混合缓存（含 Redis）
│   │   # user_profile_cache.py ← 可裁剪（仅用户画像需要）
│   │
│   ├── db/                           # [Core-partial] 数据持久层
│   │   ├── base.py                   # SQLAlchemy Engine + Session
│   │   ├── session.py                # DB Session 管理
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── message_model.py      # [Min-Biz] 消息记录
│   │   │   ├── conversation_model.py # [Min-Biz] 会话记录
│   │   │   └── knowledge_base_model.py / knowledge_file_model.py  # FAQ 所需
│   │   │   # 其余 model（symptom, treat_avg_time, doctor_schedule 等）← 可裁剪
│   │   └── repository/
│   │       ├── __init__.py           # add_message_to_db / update_message
│   │       ├── message_repository.py
│   │       ├── conversation_repository.py
│   │       └── knowledge_base_repository.py / knowledge_file_repository.py
│   │       # 其余 repository ← 可裁剪
│   │
│   ├── chat/                         # [Core] 对话调度与上下文工程
│   │   ├── dynamic_dispatch.py       # ★ 总调度器（Dispatcher + SSEStreamer）
│   │   ├── context_engineering.py    # ★ 主题/任务/阶段/槽位识别
│   │   ├── slot_extractor.py         # 槽位抽取服务
│   │   ├── process_proxy.py          # ProcessProxy 基类
│   │   ├── utils.py                  # 缓存 key 常量、辅助函数
│   │   ├── conversation_summary_manager.py  # 对话摘要（异步）
│   │   └── direct_task_shortcut.py   # 一句话直接路由（快捷路径）
│   │   # 以下可裁剪（非主链路）：
│   │   # knowledge_base_chat*.py / search_engine_chat.py / file_chat.py
│   │   # pre_consultation*.py / chat_range_process_proxy.py
│   │   # common_qa_process_proxy.py / graph_rag_process_proxy.py
│   │
│   ├── agents/                       # 智能体工具层
│   │   ├── abstract_tool.py          # [Core] 工具基类（继承 LangChain BaseTool）
│   │   ├── agent_service.py          # [Core] AgentServiceFactory（授权+工具注册）
│   │   ├── agents_process_proxy.py   # [Core] AgentsProcessProxy（工具执行代理）
│   │   ├── current_context.py        # [Core] ContextVar 线程/协程隔离
│   │   ├── tool_direct_result.py     # [Core] BaseToolDirectResult（结构化响应）
│   │   ├── tool_params.py            # [Core] 工具参数约定
│   │   ├── faq_retrieval.py          # [Min-Biz] FAQ 检索（get_other 依赖）
│   │   ├── dateUtil.py               # [Min-Biz] 日期工具（通用）
│   │   ├── get_other.py              # [Min-Biz] ★ 最小业务工具：通用问答
│   │   │
│   │   ├── interceptors/             # [Core-partial] 拦截器框架
│   │   │   └── tool_interceptor.py   # 拦截器基类 + 注册
│   │   │   # 其余具体拦截器 ← 可裁剪
│   │   │
│   │   # ---- 以下全部可裁剪（按需引入） ----
│   │   # get_doctor.py / get_dept.py / get_report.py ...（40+ 业务工具）
│   │   # ai_triage/ （导诊专用工具子目录）
│   │
│   ├── knowledge_base/               # [Min-Biz] FAQ/知识库支撑
│   │   ├── utils.py                  # get_chain / get_llm_chain 等
│   │   ├── migrate.py                # init_system / create_tables
│   │   ├── faq_builder.py            # FAQ 向量构建
│   │   └── kb_api.py                 # 知识库管理 API（可选，调试用）
│   │
│   ├── util/                         # [Core] 工具类
│   │   ├── task_pool.py              # TaskPoolExecutor（线程池任务管理）
│   │   └── json_rule_engine.py       # JSON 规则引擎（工具路由辅助）
│   │
│   └── job/                          # [Core-partial] 定时任务
│       ├── scheduler/scheduler_register.py  # 调度器注册（启动依赖）
│       └── xxl_job/xxljobconfig.py   # XXL-Job lifespan（若不用可 mock）
│
├── text_splitter/                    # [Min-Biz] 中文文本切分（FAQ 构建需要）
│   ├── chinese_recursive_text_splitter.py
│   └── chinese_text_splitter.py
│
└── nltk_data/                        # [Min-Biz] 分词数据（离线用）
    └── tokenizers/punkt/...
```

## 最小调用链路

```
POST /api/v1/chat/completions
        │
        ▼
  dynamic_dispatch.py           → Dispatcher._acquire / _prepare
        │
        ▼
  context_engineering.py        → 主题识别 → 任务识别 → 槽位抽取
        │
        ▼
  agents_process_proxy.py       → AgentServiceFactory.get_service()
        │                           根据 tasks.yaml 路由到工具名
        ▼
  agents/get_other.py           → FAQ检索 + LLM流式生成
        │
        ▼
  callback_handler/             → SSE 流式推送
  stream_callback_handler.py
        │
        ▼
  process_proxy.post_process()  → 写 DB（message）+ 更新会话缓存
```

tasks.yaml 业务地图 + agent_service.py 授权注册 + get_other.py 兜底工具 三者是最小业务单元，去掉任意一个，整条链路导致路由失败或工具找不到