# 股票模拟预测系统开发文档（基于现有代码反推）

> 文档目的：对当前代码实现进行“架构梳理 + 需求反推 + 接口翻译”，帮助新开发者快速理解系统并继续迭代。

## 1. 项目定位与边界

### 1.1 项目定位
本系统是一个**娱乐/研究级**股票趋势模拟器，核心通过：
- 新闻文本（或实时新闻标题）作为输入种子；
- 轻量知识图谱（实体-事件-情绪）承载证据；
- 多智能体（bull/bear）进行贝叶斯风格更新；
- 输出趋势概率与情绪曲线。

### 1.2 非目标
- 不提供真实投资建议；
- 不保证金融预测准确性；
- 不包含生产级交易、鉴权、监控、持久化。

---

## 2. 总体架构

系统分为三层：

1. **仿真引擎层**（`stock_simulation.py`）
   - 图谱构建、实体抽取、情绪评分、智能体创建、环境配置、模拟更新、报告生成。
2. **服务与接口层**（`web_ui.py`）
   - HTTP 路由、payload 转换、调用引擎函数并返回 JSON。
3. **前端展示层**（`ui/index.html`）
   - 表单输入参数，调用 API，显示预测结果。

---

## 3. 核心模块设计（`stock_simulation.py`）

### 3.1 数据结构
- `Graph`
  - 自定义轻量图结构。
  - 对外暴露：`add_node`、`add_edge`、`edges`、`number_of_edges`。
- `SimulationConfig`
  - 仿真参数容器：`steps`、`disturb_prob`、`time_speed`、`seed`。

### 3.2 图谱与输入处理
- `_validate_news(news)`
  - 校验新闻字符串非空且小于 10KB。
- `extract_entities(news)`
  - 规则提取实体：中文“公司X”片段 + 英文大写 ticker。
- `_score_sentiment(news)`
  - 使用关键词集合估计情绪倾向，映射到 `[0.05, 0.95]`。
- `build_graph(news)`
  - 构建 `实体 -> 新闻事件 -> 市场情绪` 结构并注入 `weight`。

### 3.3 即时信息拉取
- `fetch_real_time_news(ticker, provider, api_key, limit, timeout)`
  - provider=`polygon`：调用 Polygon 新闻接口（需要 key）。
  - provider=`yfinance`：调用 Yahoo Finance 搜索新闻端点。
  - 返回拼接后的标题文本，供 `build_graph` 使用。

### 3.4 智能体与环境
- `create_agents(num)`
  - 交替创建 `bull/bear`。
  - 初始化先验：bull `(2,1)`、bear `(1,2)`。
- `configure_environment(config)`
  - 校验与归一化参数（步数>0，扰动概率在 [0,1]）。

### 3.5 仿真机制
- `_graph_likelihood(graph)`
  - 读取边权均值作为证据似然；禁止负权重。
- `_social_influence(agents)`
  - 取上一轮群体均值作为社交影响项。
- `simulate(agents, graph, env, evidence_scale, interaction_strength, disturbance_events)`
  - 每轮更新：
    - `interact_likelihood = (1-s)*likelihood + s*crowd`
    - `post_alpha = alpha + interact_likelihood * evidence_scale`
    - `post_beta = beta + (1-interact_likelihood) * evidence_scale`
  - 按 `disturb_prob` 注入事件库扰动（如监管利好/黑天鹅）。
  - 返回：`(平均后验概率, 每步情绪序列)`。

### 3.6 输出与校验
- `render_emotion_curve(step_series)`
  - 将情绪序列映射为 sparkline 文本条。
- `generate_report(posterior, step_series, lang)`
  - 中英文报告，含趋势判断、概率、情绪曲线、免责声明。
- `validate_with_history(prices, posterior)`
  - 简化回测：比较预测方向与真实区间涨跌方向。

### 3.7 顶层调用接口
- `predict_stock(...)`
  - 单股票主入口：支持 `news` 直接输入，或 `ticker` 实时拉取。
- `predict_portfolio(news_map, ...)`
  - 组合入口：对多 ticker 分别模拟并返回字典结果。

---

## 4. Web 层设计（`web_ui.py` + `ui/index.html`）

### 4.1 API 路由
- `GET /`
  - 返回静态页面 `ui/index.html`。
- `POST /api/predict`
  - 请求体参数转给 `predict_stock`。
- `POST /api/portfolio`
  - 请求体参数转给 `predict_portfolio`。

### 4.2 payload 适配函数
- `predict_from_payload(payload)`
  - 负责类型转换（`int/float`）和默认值填充。
- `portfolio_from_payload(payload)`
  - 校验 `news_map` 结构并转发到组合预测。

### 4.3 前端页面能力
- 单股票预测卡片：新闻文本、ticker、provider、步数、智能体数、扰动概率、语言。
- 组合预测卡片：JSON 输入 `ticker -> news`。
- 前端通过 `fetch` 调用 API 并将结果写入 `<pre>`。

---

## 5. 关键流程时序（文本版）

### 5.1 单股票（离线）
1. 用户输入新闻。
2. `predict_stock` 调用 `build_graph`。
3. `create_agents` + `configure_environment`。
4. `simulate` 进行多轮后验更新。
5. `generate_report` 输出文本报告。

### 5.2 单股票（实时）
1. 用户输入 ticker。
2. `fetch_real_time_news` 拉取新闻标题。
3. 后续流程同离线（构图 -> 模拟 -> 报告）。

### 5.3 组合模拟
1. 前端/调用方提供 `news_map`。
2. `predict_portfolio` 逐 ticker 执行单票模拟。
3. 聚合为 `{ticker: posterior}` 返回。

---

## 6. 测试策略（当前实现）

测试文件：
- `tests/test_stock_simulation.py`
- `tests/test_web_ui.py`

覆盖点：
- 实体提取、图谱构建、边权合法性；
- 实时新闻拉取（通过 monkeypatch 模拟网络）；
- 仿真更新、报告输出、组合预测、历史校验；
- Web payload 转换函数的输入输出。

---

## 7. 与需求的映射关系（反推）

- 多智能体：已实现（bull/bear + memory + prior）。
- 贝叶斯更新：已实现（alpha/beta 后验迭代）。
- 图谱：已实现（轻量 Graph + 边权似然）。
- 动态干预：已实现（扰动事件库 + 概率注入）。
- 报告输出：已实现（双语 + 情绪曲线）。
- CLI/UI：已实现（`stock_simulation.py` + `web_ui.py` + `ui/index.html`）。
- 实时信息：已实现（Polygon / yfinance）。

---

## 8. 后续可迭代路线（建议）

1. **实体抽取升级**：接入 LLM / GraphRAG，提高事件与关系质量。
2. **概率模型升级**：从 Beta 扩展到 Dirichlet / 时序模型。
3. **智能体交互升级**：引入显式消息机制与角色网络结构。
4. **回测升级**：接入真实历史数据做窗口化评估。
5. **可视化升级**：加入图谱和曲线图（如 matplotlib / ECharts）。
6. **工程化升级**：日志分级、错误码、配置文件、部署脚本。

---

## 9. 快速上手（给新开发者）

```bash
# 1) 运行测试
pytest -q

# 2) CLI 演示
python stock_simulation.py

# 3) 启动 UI
python web_ui.py
# 打开 http://localhost:8000
```

如需看入口函数，请先从：
- `predict_stock`
- `predict_portfolio`
- `predict_from_payload`
- `portfolio_from_payload`
开始阅读。
