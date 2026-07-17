"""
统一日志配置

- 终端输出：INFO 级别，开发时实时查看
- 文件轮转：INFO 级别，logs/app.log，10MB/文件，保留 5 个历史文件
- 第三方库静默：pymilvus, httpx, urllib3 等设为 WARNING
"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

_initialized = False


def setup_logging():
    """初始化日志系统（幂等，多次调用不会重复注册 handler）"""
    global _initialized
    if _initialized:
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # root 放最低，由各 handler 控制实际级别

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- 终端 handler (INFO) ---
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    # --- 文件 handler (INFO, 自动轮转) ---
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # --- 第三方库降噪 ---
    for lib in ("pymilvus", "httpx", "httpcore", "urllib3", "openai", "jieba", "PIL"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    _initialized = True
    logging.getLogger(__name__).info("Logging initialized: file=%s", LOG_FILE)
