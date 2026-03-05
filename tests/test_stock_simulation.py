import json

import pytest

from stock_simulation import (
    DISTURBANCE_EVENTS,
    Graph,
    build_graph,
    configure_environment,
    create_agents,
    extract_entities,
    fetch_real_time_news,
    generate_report,
    predict_portfolio,
    predict_stock,
    predict_stock_detailed,
    render_emotion_curve,
    simulate,
    validate_with_history,
)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_extract_entities_returns_company_and_ticker():
    entities = extract_entities("公司A 与 AAPL 发布积极财报")
    assert "AAPL" in entities
    assert any(item.startswith("公司") for item in entities)


def test_build_graph_returns_graph_with_weighted_edges():
    graph = build_graph("公司A发布积极财报，盈利增长")
    assert graph.number_of_edges() >= 2
    for _, _, data in graph.edges(data=True):
        assert 0 <= data["weight"] <= 1


def test_build_graph_rejects_invalid_news():
    with pytest.raises(ValueError):
        build_graph("")


def test_fetch_real_time_news_polygon(monkeypatch):
    def fake_urlopen(url, timeout=8):
        assert "polygon" in url
        return _FakeResponse({"results": [{"title": "AAPL beats expectations"}]})

    monkeypatch.setattr("stock_simulation.urlopen", fake_urlopen)
    text = fetch_real_time_news("AAPL", provider="polygon", api_key="demo")
    assert "AAPL beats expectations" in text


def test_fetch_real_time_news_yfinance(monkeypatch):
    def fake_urlopen(url, timeout=8):
        assert "yahoo" in url
        return _FakeResponse({"news": [{"title": "Apple launches new product"}]})

    monkeypatch.setattr("stock_simulation.urlopen", fake_urlopen)
    text = fetch_real_time_news("AAPL", provider="yfinance")
    assert "Apple launches new product" in text


def test_create_agents_mixed_roles_and_motivation():
    agents = create_agents(5)
    assert len(agents) == 5
    assert agents[0]["role"] == "bull"
    assert agents[1]["role"] == "bear"


def test_configure_environment_validates_steps():
    with pytest.raises(ValueError):
        configure_environment({"steps": 0})


def test_simulate_updates_memory_and_returns_probability_and_curve():
    graph = build_graph("positive growth beat profit")
    agents = create_agents(4)
    env = configure_environment({"steps": 5, "disturb_prob": 0.0, "seed": 1})

    posterior, series = simulate(agents, graph, env)

    assert 0 <= posterior <= 1
    assert len(series) == 5
    assert all(len(agent["memory"]) == 5 for agent in agents)


def test_simulate_rejects_negative_weight():
    graph = Graph()
    graph.add_edge("A", "B", weight=-0.2)
    agents = create_agents(2)
    env = configure_environment()

    with pytest.raises(ValueError):
        simulate(agents, graph, env)


def test_disturbance_event_library_non_empty():
    assert DISTURBANCE_EVENTS


def test_generate_report_supports_zh_and_en_with_curve():
    zh_report = generate_report(0.7, step_series=[0.4, 0.6], lang="zh")
    en_report = generate_report(0.3, step_series=[0.5], lang="en")
    assert "上涨" in zh_report
    assert "情绪曲线" in zh_report
    assert "DOWN" in en_report
    assert "EmotionCurve" in en_report


def test_render_emotion_curve_outputs_text_bar():
    curve = render_emotion_curve([0.1, 0.4, 0.9])
    assert len(curve) == 3


def test_validate_with_history_direction_match():
    result = validate_with_history([100, 110], posterior=0.8)
    assert result["direction_match"] is True


def test_predict_stock_end_to_end_returns_report_text():
    report = predict_stock(news="公司A积极财报，市场增长", num_agents=5, steps=10, seed=42)
    assert "预测趋势" in report
    assert "概率" in report


def test_predict_stock_can_use_ticker_provider(monkeypatch):
    monkeypatch.setattr(
        "stock_simulation.fetch_real_time_news",
        lambda **kwargs: "positive growth profit",
    )
    report = predict_stock(news=None, ticker="AAPL", news_provider="polygon", api_key="demo")
    assert "预测趋势" in report


def test_predict_portfolio_multi_ticker():
    result = predict_portfolio({"AAPL": "positive growth", "TSLA": "decline risk"}, steps=5)
    assert set(result.keys()) == {"AAPL", "TSLA"}
    assert all(0 <= value <= 1 for value in result.values())


def test_predict_stock_detailed_contains_process_fields():
    detail = predict_stock_detailed(news="公司A积极财报，市场增长", num_agents=4, steps=6, seed=7)
    assert "report" in detail
    assert "process" in detail
    assert len(detail["process"]) >= 5
    assert 0 <= detail["posterior"] <= 1
