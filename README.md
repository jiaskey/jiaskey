# 股票模拟预测系统（Stock Simulation Prediction System）

> 基于多智能体群体智能 + 贝叶斯更新的娱乐级股票趋势模拟工具。

## 免责声明
本项目**不构成投资建议**，仅用于思想实验、研究与工程示例。

## 已实现能力（本版）
- 新闻/财报文本输入，构建简化知识图谱
- 轻量实体提取（公司名 / ticker）
- 多角色智能体（bull/bear）先验注入 + 记忆演化
- 贝叶斯后验更新 + 智能体社交影响（interaction）
- 扰动事件库注入（非纯随机倍数）
- 中文/英文预测报告输出
- 情绪曲线文本可视化（sparkline）
- 可选近实时新闻拉取（Polygon / Yahoo Finance endpoint）
- 多股票组合模拟 `predict_portfolio`
- 简化历史价格方向校验 `validate_with_history`

## 环境
- Python 3.10+
- 依赖：`pytest`（测试）

## 安装
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用
### 1) 离线手动输入新闻
```python
from stock_simulation import predict_stock

news = "公司A发布积极财报，盈利增长，市场预期上调。"
print(predict_stock(news=news, num_agents=5, steps=10, seed=42))
```

### 2) 即时信息：按股票代码拉取新闻再预测
```python
from stock_simulation import predict_stock

report = predict_stock(
    news=None,
    ticker="AAPL",
    news_provider="polygon",  # 或 "yfinance"
    api_key="YOUR_POLYGON_KEY",  # yfinance 可不填
)
print(report)
```

### 3) 多股票组合模拟
```python
from stock_simulation import predict_portfolio

result = predict_portfolio({
    "AAPL": "positive growth and product momentum",
    "TSLA": "delivery risk and margin pressure",
})
print(result)
```

### 4) 历史方向校验
```python
from stock_simulation import validate_with_history

print(validate_with_history([100, 102, 110], posterior=0.72))
```

### 5) 前端 UI
```bash
python web_ui.py
# 浏览器打开 http://localhost:8000
```

UI 提供：
- 单股票预测（支持手动 news 或 ticker 拉取）
- 组合预测（JSON 输入多股票新闻）

## CLI 运行示例
```bash
python stock_simulation.py
```


## 如何演示该系统（推荐流程）
1. **准备环境**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **命令行快速演示（离线）**
```bash
python stock_simulation.py
```
你会看到一段中文预测报告（趋势概率 + 情绪曲线）。

3. **启动 Web UI 演示（最直观）**
```bash
python web_ui.py
```
然后打开浏览器访问 `http://localhost:8000`：
- 在“单股票预测”里直接填新闻，点击“运行预测”。
- 或者留空新闻，填 `ticker` + provider（`yfinance`/`polygon`）进行实时新闻模式。
- 在“组合预测”里粘贴 JSON（如 `{"AAPL": "positive growth", "TSLA": "decline risk"}`）点击运行。

4. **API 演示（便于录屏/自动化）**
新开一个终端，执行：
```bash
curl -s http://localhost:8000/api/predict \
  -H 'Content-Type: application/json' \
  -d '{"news":"公司A积极财报，盈利增长","num_agents":5,"steps":10}'
```

组合预测示例：
```bash
curl -s http://localhost:8000/api/portfolio \
  -H 'Content-Type: application/json' \
  -d '{"news_map":{"AAPL":"positive growth","TSLA":"decline risk"},"steps":8}'
```

5. **验证演示环境**
```bash
pytest -q
```

## 测试
```bash
pytest -q
```

## 代码结构
- `stock_simulation.py`：核心模块
  - `extract_entities`
  - `build_graph`
  - `fetch_real_time_news`
  - `create_agents`
  - `configure_environment`
  - `simulate`
  - `render_emotion_curve`
  - `generate_report`
  - `validate_with_history`
  - `predict_stock`
  - `predict_portfolio`
- `web_ui.py`：内置 HTTP 服务与 API 路由
- `ui/index.html`：前端页面（表单 + 调用 API）
- `tests/test_stock_simulation.py`：单元与集成测试
- `tests/test_web_ui.py`：UI API 载荷转换测试


## 开发文档
- 详见 `DEVELOPMENT_DOC.md`（代码反推与架构说明）。
