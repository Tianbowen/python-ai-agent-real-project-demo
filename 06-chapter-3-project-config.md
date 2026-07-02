# 项目骨架 + 配置层

## 创建目录结构

文件夹：common, models, cache, callback, context_engine, agents, dispatch, db, playground

每个文件夹创建__init__.py 让每个目录成为python包

### 创建 requirements.txt

根目录创建 requirements.txt 写入
```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
sse-starlette==2.1.3
langchain==0.3.7
langchain-core==0.3.15
langchain-openai==0.2.6
pydantic==2.9.2
cachetools==5.5.0
PyYAML==6.0.2
httpx==0.27.2
```

```bash
# 执行
pip install -r requirements.txt
```