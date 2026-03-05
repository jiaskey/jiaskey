import pytest

from web_ui import portfolio_from_payload, predict_from_payload


def test_predict_from_payload_with_news():
    result = predict_from_payload({"news": "公司A积极财报，盈利增长", "num_agents": 4, "steps": 5})
    assert result["ok"] is True
    assert "report" in result
    assert "process" in result
    assert "posterior" in result


def test_predict_from_payload_requires_news_or_ticker():
    with pytest.raises(ValueError):
        predict_from_payload({"news": None, "ticker": None})


def test_portfolio_from_payload_returns_dict():
    result = portfolio_from_payload({"news_map": {"AAPL": "positive growth", "TSLA": "decline risk"}, "steps": 5})
    assert result["ok"] is True
    assert set(result["result"].keys()) == {"AAPL", "TSLA"}
