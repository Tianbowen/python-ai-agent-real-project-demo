# db/todo_db.py
# 内存数据库

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _tomorrow() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

@dataclass
class TodoItem:
    """Todo 记录"""
    id: str
    title: str
    due_date: Optional[str] = None
    priority: str = "中"
    done: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

class TodoDB:
    """
    内存 Todo 数据库

    """

    def __init__(self):
        self._store: Dict[str, TodoItem] = {}        

    # 对外接口
    def list_all(self) -> List[TodoItem]:
        """查询用户所有代办"""
        return list(self._store.values())
    
    def list_today(self) -> List[TodoItem]:
        """查询今天的代办"""
        today = _today()
        return [
            t for t in self._store.values() 
            if t.due_date and t.due_date.startswith(today)
        ]
    
    def create(self, title: str, due_date: str = None, priority: str = "中") -> TodoItem:
        """
        新增一条代办
        due_date 传入格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM
        调用方(create_todo工具) 负责将自然语言转成该格式
        """
        item = TodoItem(
            id=uuid.uuid4().hex[:8],
            title=title,
            due_date=due_date,
            priority=priority
        )
        self._store[item.id] = item
        return item
    
    def complete(self, title_keyword: str) -> Optional[TodoItem]:
        """按标题关键词标记删除"""
        for item in self._store.values():
            if title_keyword in item.title and not item.done:
                item.done = True
                return item
        return None

# 全局单例
todo_db = TodoDB()
    