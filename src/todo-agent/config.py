import os
import logging
from contextvars import ContextVar
from pathlib import Path


# ══════════════════════════════════════════════
#  配置文件加载
#
#  加载顺序（优先级从高到低）：
#  1. 系统已有的环境变量（生产部署时通过容器注入）
#  2. 项目根目录的 .env 文件（本地开发使用）
#  3. 代码里的 os.getenv 默认值
#
#  override=False：不覆盖系统已有的环境变量
#  这样生产环境只需设置系统变量，不需要 .env 文件
# ══════════════════════════════════════════════

from dotenv import load_dotenv
# __file__ 内置变量 代表当前文件的路径
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)
    print(f"[Config] 已加载配置文件:{_env_path}")
else:
    print(f"[Config] 未找到.env文件，使用默认值")

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
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# ==========================
# 服务配置
# ==========================

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "5000"))

# ==========================
# 并发控制：同时最多处理多少请求
# 设太小：排队严重，设太大：LLM / 内存撑不住
# ==========================

MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "20"))

# ==========================
# 会话缓存配置
# TTL = 会话超时时间(秒), 30分钟无操作自动清除
# ==========================

SESSION_TTL_S = int(os.getenv("SESSION_TTL_S", "1800"))  # 30分钟
SESSION_MAXSIZE = int(os.getenv("SESSION_MAXSIZE", "10000"))

# ==========================
# 业务配置
# ==========================
TASKS_YAML_PATH = os.getenv("TASKS_YAML_PATH", "tasks.yaml")
HISTORY_MAX = int(os.getenv("HISTORY_MAX", "20")) # 每个会话最多保留20轮历史
CHAT_TIMEOUT_S = 60 # 单次请求最大超时

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