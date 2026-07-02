import os
import logging
from contextvars import ContextVar

# ==========================
# LLM 配置
# 使用 os.getenv 读取环境变量，方便不同环境切换
# 开发时在 terminal set 即可：
#   export LLM_API_BASE= "http://localhost:5000/v1"
# ==========================

LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "0248"))

# ==========================
# 服务配置
# ==========================

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_POST", "5000"))

# ==========================
# 并发控制：同时最多处理多少请求
# 设太小：排队严重，设太大：LLM / 内存撑不住
# ==========================

MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "20"))

# ==========================
# 会话缓存配置
# TTL = 会话超时时间(秒), 30分钟无操作自动清除
# ==========================

SESSION_TTL_S = os.getenv("SESSION_TTL_S", "1800")  # 30分钟
SESSION_MAXSIZE = os.getenv("SESSION_MAXSIZE", "10000")

# ==========================
# 业务配置
# ==========================
TASKS_YAML_PATH = os.getenv("TASKS_YAML_PATH", "tasks.yaml")
HISTORY_MAX = int(os.getenv("HISTORY_MAX", "20")) # 每个会话最多保留20轮历史

# ==========================
# 日志
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
)
logger = logging.getLogger("todo-agent")

# ==========================
# ContextVar: 每个请求的 trace_id
# 用于在日志中追踪同一个请求的所有操作
# ==========================

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# ==========================
# YAML 加载（延时加载，启动时才读文件）
# ==========================

_tasks_cache: dict = {}

def load_tasks_yaml() -> dict:
    """加载业务地图配置，缓存避免重复 IO"""
    global _tasks_cache
    if not _tasks_cache:
        import yaml
        with open(TASKS_YAML_PATH, "r", encoding="utf-8") as f:
            _tasks_cache = yaml.safe_load(f)
    return _tasks_cache