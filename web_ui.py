"""Simple web UI server for stock simulation prediction."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from stock_simulation import predict_portfolio, predict_stock_detailed

UI_DIR = Path(__file__).resolve().parent / "ui"


def _json_response(handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def predict_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    news = payload.get("news")
    ticker = payload.get("ticker")
    num_agents = int(payload.get("num_agents", 5))
    steps = int(payload.get("steps", 10))
    disturb_prob = float(payload.get("disturb_prob", 0.2))
    seed = payload.get("seed", 42)

    detail = predict_stock_detailed(
        news=news,
        ticker=ticker,
        num_agents=num_agents,
        steps=steps,
        disturb_prob=disturb_prob,
        seed=None if seed in (None, "") else int(seed),
        news_provider=str(payload.get("news_provider", "polygon")),
        api_key=payload.get("api_key"),
        lang=str(payload.get("lang", "zh")),
    )
    return {"ok": True, **detail}


def portfolio_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    news_map = payload.get("news_map", {})
    if not isinstance(news_map, dict):
        raise ValueError("news_map must be an object")

    result = predict_portfolio(
        news_map={str(k): str(v) for k, v in news_map.items()},
        num_agents=int(payload.get("num_agents", 5)),
        steps=int(payload.get("steps", 10)),
        seed=None if payload.get("seed") in (None, "") else int(payload.get("seed")),
    )
    return {"ok": True, "result": result}


class UIHandler(BaseHTTPRequestHandler):
    def _serve_index(self) -> None:
        html = (UI_DIR / "index.html").read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._serve_index()
            return
        _json_response(self, {"ok": False, "error": "Not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length) or b"{}")

            if self.path in ("/api/predict", "/api/process"):
                _json_response(self, predict_from_payload(payload))
                return
            if self.path == "/api/portfolio":
                _json_response(self, portfolio_from_payload(payload))
                return
            _json_response(self, {"ok": False, "error": "Not found"}, status=404)
        except Exception as exc:
            _json_response(self, {"ok": False, "error": str(exc)}, status=400)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), UIHandler)
    print(f"UI running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
