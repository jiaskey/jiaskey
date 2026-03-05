"""娱乐级股票模拟预测系统核心模块。"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

logger = logging.getLogger(__name__)


class Graph:
    """轻量无依赖图结构（兼容本项目所需接口）。"""

    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[tuple[str, str, dict[str, Any]]] = []

    def add_node(self, node: str, **attrs: Any) -> None:
        self._nodes[node] = attrs

    def add_edge(self, src: str, dst: str, **attrs: Any) -> None:
        self._edges.append((src, dst, attrs))

    def edges(self, data: bool = False):
        if data:
            return list(self._edges)
        return [(src, dst) for src, dst, _ in self._edges]

    def number_of_edges(self) -> int:
        return len(self._edges)


@dataclass
class SimulationConfig:
    steps: int = 10
    disturb_prob: float = 0.2
    time_speed: str = "fast"
    seed: int | None = None


DISTURBANCE_EVENTS: dict[str, float] = {
    "监管利好": 1.15,
    "监管利空": 0.85,
    "行业突破": 1.2,
    "黑天鹅": 0.7,
}

POSITIVE_KEYWORDS = {
    "积极", "增长", "盈利", "创新", "利好", "positive", "growth", "beat", "profit", "up"
}
NEGATIVE_KEYWORDS = {
    "亏损", "下滑", "风险", "利空", "negative", "decline", "loss", "down", "miss"
}


def _validate_news(news: str) -> None:
    if not isinstance(news, str) or not news.strip():
        raise ValueError("news must be a non-empty string")
    if len(news.encode("utf-8")) > 10 * 1024:
        raise ValueError("news text too long; max 10KB")


def extract_entities(news: str) -> list[str]:
    """轻量实体提取（规则版）。

    提取中文/英文大写股票代码或“公司X”等片段，模拟 GraphRAG 的输入。
    """
    _validate_news(news)
    zh_entities = re.findall(r"公司[A-Za-z0-9一-龥]{1,12}", news)
    en_tickers = re.findall(r"\b[A-Z]{2,5}\b", news)
    entities = list(dict.fromkeys(zh_entities + en_tickers))
    return entities or ["目标公司"]


def _score_sentiment(news: str) -> float:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", news.lower())
    if not tokens:
        return 0.5
    pos = sum(token in POSITIVE_KEYWORDS for token in tokens)
    neg = sum(token in NEGATIVE_KEYWORDS for token in tokens)
    return min(0.95, max(0.05, (pos + 1) / (pos + neg + 2)))


def build_graph(news: str) -> Graph:
    _validate_news(news)
    sentiment = _score_sentiment(news)
    entities = extract_entities(news)

    graph = Graph()
    event_node = "新闻事件"
    sentiment_node = "市场情绪"
    graph.add_node(event_node, type="event", text=news.strip())
    graph.add_node(sentiment_node, type="signal")

    for entity in entities:
        graph.add_node(entity, type="entity")
        graph.add_edge(entity, event_node, relation="披露", weight=sentiment)

    graph.add_edge(event_node, sentiment_node, relation="影响", weight=sentiment)
    return graph


def fetch_real_time_news(
    ticker: str,
    provider: str = "polygon",
    api_key: str | None = None,
    limit: int = 5,
    timeout: int = 8,
) -> str:
    """拉取近实时新闻并拼接为种子文本。"""
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker must be non-empty")
    if limit <= 0:
        raise ValueError("limit must be > 0")

    provider_name = provider.lower()
    logger.info("fetching realtime news: provider=%s ticker=%s", provider_name, ticker)

    if provider_name == "polygon":
        if not api_key:
            raise ValueError("polygon provider requires api_key")
        query = urlencode({"ticker": ticker, "limit": limit, "apiKey": api_key})
        url = f"https://api.polygon.io/v2/reference/news?{query}"
        with urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        items = payload.get("results", [])
        titles = [item.get("title", "") for item in items if item.get("title")]
        if not titles:
            raise ValueError("no news returned from polygon")
        return "\n".join(titles)

    if provider_name == "yfinance":
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={ticker}&newsCount={limit}"
        with urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        items = payload.get("news", [])
        titles = [item.get("title", "") for item in items if item.get("title")]
        if not titles:
            raise ValueError("no news returned from yfinance endpoint")
        return "\n".join(titles)

    raise ValueError("unsupported provider; choose polygon or yfinance")


def create_agents(num: int = 5) -> list[dict[str, Any]]:
    if num <= 0:
        raise ValueError("num_agents must be > 0")

    agents = []
    for idx in range(num):
        role = "bull" if idx % 2 == 0 else "bear"
        prior = (2.0, 1.0) if role == "bull" else (1.0, 2.0)
        motivation = "增长追求" if role == "bull" else "风险规避"
        agents.append({"id": idx, "role": role, "prior": prior, "memory": [], "motivation": motivation})
    return agents


def configure_environment(config: dict[str, Any] | None = None) -> SimulationConfig:
    if config is None:
        return SimulationConfig()
    steps = int(config.get("steps", 10))
    disturb_prob = float(config.get("disturb_prob", 0.2))
    if steps <= 0:
        raise ValueError("steps must be > 0")
    if not 0 <= disturb_prob <= 1:
        raise ValueError("disturb_prob must be in [0, 1]")
    seed = config.get("seed")
    return SimulationConfig(
        steps=steps,
        disturb_prob=disturb_prob,
        time_speed=str(config.get("time_speed", "fast")),
        seed=None if seed is None else int(seed),
    )


def _graph_likelihood(graph: Graph) -> float:
    if graph.number_of_edges() == 0:
        return 0.5
    weights = [data.get("weight", 0.5) for _, _, data in graph.edges(data=True)]
    if any(weight < 0 for weight in weights):
        raise ValueError("graph edge weight must be non-negative")
    return min(1.0, max(0.0, sum(weights) / len(weights)))


def _social_influence(agents: list[dict[str, Any]]) -> float:
    """智能体间交互：上一轮群体均值作为社会影响项。"""
    latest = [a["memory"][-1] for a in agents if a["memory"]]
    return sum(latest) / len(latest) if latest else 0.5


def simulate(
    agents: list[dict[str, Any]],
    graph: Graph,
    env: SimulationConfig,
    evidence_scale: float = 10.0,
    interaction_strength: float = 0.2,
    disturbance_events: dict[str, float] | None = None,
) -> tuple[float, list[float]]:
    if not agents:
        raise ValueError("agents list must not be empty")

    rng = random.Random(env.seed)
    likelihood = _graph_likelihood(graph)
    posteriors: list[float] = []
    step_series: list[float] = []
    events = disturbance_events or DISTURBANCE_EVENTS

    for step in range(env.steps):
        crowd = _social_influence(agents)
        step_values: list[float] = []

        for agent in agents:
            alpha, beta_param = agent["prior"]
            interact_likelihood = (1 - interaction_strength) * likelihood + interaction_strength * crowd
            post_alpha = alpha + interact_likelihood * evidence_scale
            post_beta = beta_param + (1 - interact_likelihood) * evidence_scale
            posterior_mean = post_alpha / (post_alpha + post_beta)
            agent["prior"] = (post_alpha, post_beta)
            agent["memory"].append(posterior_mean)
            posteriors.append(posterior_mean)
            step_values.append(posterior_mean)

        if rng.random() < env.disturb_prob and events:
            event_name, factor = rng.choice(list(events.items()))
            step_values = [min(1.0, max(0.0, p * factor)) for p in step_values]
            for i, agent in enumerate(agents):
                agent["memory"][-1] = step_values[i]
                posteriors[-len(agents) + i] = step_values[i]
            logger.info("disturbance injected at step=%s event=%s factor=%.2f", step, event_name, factor)

        step_series.append(sum(step_values) / len(step_values))

    return sum(posteriors) / len(posteriors), step_series


def render_emotion_curve(step_series: list[float]) -> str:
    """输出文本火花线，便于 CLI 快速查看情绪曲线。"""
    if not step_series:
        return ""
    bars = "▁▂▃▄▅▆▇█"
    mapped = [bars[min(7, max(0, int(v * 8) - 1))] for v in step_series]
    return "".join(mapped)


def generate_report(posterior: float, step_series: list[float] | None = None, lang: str = "zh") -> str:
    curve = render_emotion_curve(step_series or [])
    if lang.lower().startswith("en"):
        trend = "UP" if posterior > 0.5 else "DOWN"
        return (
            f"Prediction: {trend} (probability: {posterior:.2f})\n"
            f"EmotionCurve: {curve}\n"
            "Disclaimer: for entertainment and thought experiments only."
        )
    trend = "上涨" if posterior > 0.5 else "下跌"
    return (
        f"预测趋势: {trend} (概率: {posterior:.2f})\n"
        f"情绪曲线: {curve}\n"
        "免责声明: 本系统仅用于娱乐与思想实验，不构成投资建议。"
    )


def validate_with_history(prices: list[float], posterior: float) -> dict[str, Any]:
    """简化回测校验：比较最新区间涨跌方向与模型方向。"""
    if len(prices) < 2:
        raise ValueError("prices should contain at least 2 values")
    if any(p <= 0 for p in prices):
        raise ValueError("prices must be positive")

    realized_up = prices[-1] > prices[0]
    predicted_up = posterior > 0.5
    return {
        "predicted_up": predicted_up,
        "realized_up": realized_up,
        "direction_match": predicted_up == realized_up,
        "price_change": prices[-1] / prices[0] - 1,
    }


def predict_stock(
    news: str | None = None,
    num_agents: int = 5,
    steps: int = 10,
    disturb_prob: float = 0.2,
    seed: int | None = 42,
    lang: str = "zh",
    ticker: str | None = None,
    news_provider: str = "polygon",
    api_key: str | None = None,
) -> str:
    """端到端执行预测。可直接传 news，或通过 ticker 拉取近实时新闻。"""
    if news is None:
        if not ticker:
            raise ValueError("either news or ticker must be provided")
        news = fetch_real_time_news(ticker=ticker, provider=news_provider, api_key=api_key)

    graph = build_graph(news)
    agents = create_agents(num_agents)
    env = configure_environment({"steps": steps, "disturb_prob": disturb_prob, "seed": seed})
    avg_posterior, step_series = simulate(agents, graph, env)
    return generate_report(avg_posterior, step_series=step_series, lang=lang)


def predict_portfolio(
    news_map: dict[str, str],
    num_agents: int = 5,
    steps: int = 10,
    seed: int | None = 42,
) -> dict[str, float]:
    """多股票组合模拟：返回每个 ticker 的后验概率。"""
    if not news_map:
        raise ValueError("news_map cannot be empty")

    results: dict[str, float] = {}
    for idx, (ticker, news) in enumerate(news_map.items()):
        graph = build_graph(f"{ticker} {news}")
        agents = create_agents(num_agents)
        env = configure_environment({"steps": steps, "seed": None if seed is None else seed + idx})
        posterior, _ = simulate(agents, graph, env)
        results[ticker] = posterior
    return results


def predict_stock_detailed(
    news: str | None = None,
    num_agents: int = 5,
    steps: int = 10,
    disturb_prob: float = 0.2,
    seed: int | None = 42,
    lang: str = "zh",
    ticker: str | None = None,
    news_provider: str = "polygon",
    api_key: str | None = None,
) -> dict[str, Any]:
    """返回结构化过程数据，供前端过程可视化使用。"""
    if news is None:
        if not ticker:
            raise ValueError("either news or ticker must be provided")
        news = fetch_real_time_news(ticker=ticker, provider=news_provider, api_key=api_key)

    entities = extract_entities(news)
    graph = build_graph(news)
    agents = create_agents(num_agents)
    env = configure_environment({"steps": steps, "disturb_prob": disturb_prob, "seed": seed})
    posterior, step_series = simulate(agents, graph, env)
    report = generate_report(posterior, step_series=step_series, lang=lang)

    edge_weights = [d.get("weight", 0.5) for _, _, d in graph.edges(data=True)]
    likelihood = sum(edge_weights) / len(edge_weights) if edge_weights else 0.5
    trend = "上涨" if posterior > 0.5 else "下跌"

    process = [
        {"name": "输入准备", "status": "done", "detail": f"输入长度 {len(news)} 字符"},
        {"name": "实体提取", "status": "done", "detail": ", ".join(entities)},
        {"name": "图谱构建", "status": "done", "detail": f"边数量 {graph.number_of_edges()}，似然 {likelihood:.2f}"},
        {"name": "智能体模拟", "status": "done", "detail": f"agents={num_agents}, steps={steps}"},
        {"name": "报告输出", "status": "done", "detail": f"{trend} ({posterior:.2f})"},
    ]

    return {
        "report": report,
        "posterior": posterior,
        "trend": trend,
        "entities": entities,
        "step_series": step_series,
        "emotion_curve": render_emotion_curve(step_series),
        "process": process,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(predict_stock(news="公司A发布积极财报，盈利增长，市场预期上调。", num_agents=5, steps=10))
