# 第一周执行表

目标：七天内完成可运行的数据导入、去重、存储与 AI 分析后端闭环。

每天建议分配：

- 项目开发：6 小时
- Python/FastAPI/数据库学习：2 小时
- 测试、文档和复盘：1 小时
- 面试基础：1 小时

## Day 1：工程环境

- 阅读 `README.md` 和 `docs/PRD.md`
- 安装并理解 `uv`
- 学习虚拟环境、依赖和环境变量
- 启动 FastAPI
- 运行测试和 Ruff
- 学习 Docker 的镜像、容器、端口、卷和 Compose 概念
- 使用 Docker Compose 启动 API、PostgreSQL 和 Redis

验收：

```bash
uv run pytest
uv run ruff check .
docker compose config
```

浏览器可以访问 `/docs` 和 `/api/v1/health`。

## Day 2：数据库

- 学习 SQLAlchemy ORM 和异步 Session
- 添加 Alembic
- 创建第一版数据库迁移
- 实现 Brand 和 Article 的新增、查询接口
- 为接口编写测试

验收：可以创建品牌并写入一条舆情数据。

## Day 3：CSV 导入

- 定义 CSV 模板
- 实现文件上传
- 校验字段和编码
- 批量写入 Article
- 返回成功、重复、失败数量
- 准备至少 100 条演示数据

验收：Swagger 中上传 CSV 后可以查询导入结果。

## Day 4：清洗与去重

- 规范化空白符、HTML 和 URL
- 使用 SHA-256 生成内容指纹
- 根据 URL 和内容指纹去重
- 记录导入失败原因
- 编写边界测试

验收：重复导入同一份 CSV 不会重复写入。

## Day 5：LLM 结构化分析

- 学习 Pydantic Schema
- 定义情感、风险类型、摘要和建议输出结构
- 编写模型客户端抽象
- 支持 OpenAI 兼容 API
- 添加超时、重试和结构校验
- 使用 Fake 客户端完成无 API Key 测试

验收：输入文章后得到稳定、可校验的 JSON 分析结果。

## Day 6：风险评分

- 将情感分、来源权重、严重关键词和传播指标组合为风险分
- 定义 low、medium、high、critical 阈值
- 保存分析记录
- 实现高风险列表 API
- 为规则编写参数化测试

验收：高风险文章可以稳定进入预警列表。

## Day 7：复盘与演示

- 清理代码和配置
- 补齐 README
- 运行全部测试和静态检查
- 录制一分钟后端演示
- 汇总本周遇到的问题
- 标记第二周任务

验收流程：

```text
上传 CSV
  → 自动清洗和去重
  → 调用 AI 分析
  → 生成风险评分
  → 查询高风险事件
```

## 第一周必须理解的知识

- Python 类型标注、异步函数、异常处理
- HTTP 方法与常见状态码
- FastAPI 路由、依赖注入、Pydantic
- SQL 主键、外键、唯一约束和事务
- Docker 镜像、容器、网络、端口和卷
- Git 分支、提交和 Pull Request

不要求一次记住全部概念。每个概念必须能结合本项目解释其作用。
