"""
public_database_login.py のテスト

ポイント:
- ブラウザ起動はモックする
- ThreadingHTTPServer は serve_forever を即時 return するモックに差し替える
- HTTP ハンドラは __new__ で生成し、ソケットを使わずに do_GET の分岐だけを確認
"""
import io
import threading
import urllib.parse
import pytest
from unittest.mock import MagicMock, patch

import public_database_login
from public_database_login import (
    TimeoutHTTPRequestHandler, ThreadingHTTPServer, login,
)


# =====================================================================
# ヘルパ
# =====================================================================
def _make_handler(path: str):
    """ソケットを使わずにハンドラを組み立てる"""
    h = TimeoutHTTPRequestHandler.__new__(TimeoutHTTPRequestHandler)
    h.path = path
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO()
    h.headers = {}
    h.request_version = "HTTP/1.1"
    h._headers_buffer = []
    h.server = MagicMock()
    # 送信系は副作用が出ないようにモック
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    h.send_error = MagicMock()
    return h


# =====================================================================
# TimeoutHTTPRequestHandler
# =====================================================================
class TestHandler:
    def setup_method(self):
        public_database_login.auth_token = None

    def test_callback_with_token_sets_global(self):
        h = _make_handler("/callback?token=abc123")
        h.do_GET()

        assert public_database_login.auth_token == "abc123"
        h.send_response.assert_called_with(200)
        # サーバーシャットダウンがスレッドで呼ばれる
        h.server.shutdown.assert_called()

    def test_callback_without_token_returns_404(self):
        h = _make_handler("/callback")
        h.do_GET()
        assert public_database_login.auth_token is None
        h.send_error.assert_called_with(404, "Not Found")

    def test_cancel_endpoint_shuts_down(self):
        h = _make_handler("/cancel")
        h.do_GET()
        assert public_database_login.auth_token is None
        h.send_response.assert_called_with(200)
        h.server.shutdown.assert_called()

    def test_unknown_path_returns_404(self):
        h = _make_handler("/some/other/path")
        h.do_GET()
        h.send_error.assert_called_with(404, "Not Found")

    def test_callback_token_is_percent_decoded(self):
        # parse_qs は自動で URL デコードする
        h = _make_handler("/callback?token=a%20b")
        h.do_GET()
        assert public_database_login.auth_token == "a b"

    def test_log_message_is_silent(self, capsys):
        h = _make_handler("/")
        h.log_message("format %s", "arg")
        captured = capsys.readouterr()
        # 何も出力しない（pass している）
        assert captured.out == "" and captured.err == ""

    def test_callback_response_contains_html(self):
        h = _make_handler("/callback?token=xyz")
        h.do_GET()
        body = h.wfile.getvalue().decode("utf-8")
        assert "認証が完了" in body or "callback" in body.lower() or "<html>" in body.lower()


# =====================================================================
# ThreadingHTTPServer.handle_timeout
# =====================================================================
class TestThreadingHTTPServer:
    def test_handle_timeout_shuts_down(self, capsys):
        server = ThreadingHTTPServer.__new__(ThreadingHTTPServer)
        server.shutdown = MagicMock()
        server.handle_timeout()
        server.shutdown.assert_called_once()
        captured = capsys.readouterr()
        assert "タイムアウト" in captured.out


# =====================================================================
# login
# =====================================================================
class TestLogin:
    def setup_method(self):
        public_database_login.auth_token = None

    def _patch_server(self, monkeypatch, serve_forever):
        fake_server = MagicMock()
        fake_server.server_address = ("localhost", 12345)
        fake_server.serve_forever = serve_forever
        fake_server.__enter__ = MagicMock(return_value=fake_server)
        fake_server.__exit__ = MagicMock(return_value=False)

        server_cls = MagicMock(return_value=fake_server)
        monkeypatch.setattr(
            "public_database_login.ThreadingHTTPServer", server_cls)
        monkeypatch.setattr(
            "public_database_login.webbrowser.open", MagicMock())
        return fake_server, server_cls

    def test_login_returns_none_on_timeout(self, monkeypatch):
        # serve_forever が即座に戻る = タイムアウト／キャンセル相当
        self._patch_server(monkeypatch, serve_forever=lambda: None)
        result = login("http://example.com")
        assert result is None

    def test_login_returns_token_when_callback_fires(self, monkeypatch):
        def fake_serve_forever():
            # コールバックでトークンがセットされた状況を模擬
            public_database_login.auth_token = "TOKEN-XYZ"

        self._patch_server(monkeypatch, serve_forever=fake_serve_forever)
        result = login("http://example.com")
        assert result == "TOKEN-XYZ"

    def test_login_opens_browser_with_encoded_redirect(self, monkeypatch):
        fake_server, server_cls = self._patch_server(
            monkeypatch, serve_forever=lambda: None)
        open_mock = MagicMock()
        monkeypatch.setattr(
            "public_database_login.webbrowser.open", open_mock)

        login("http://example.com")

        open_mock.assert_called_once()
        url = open_mock.call_args.args[0]
        assert url.startswith("http://example.com/login?redirect_uri=")
        # redirect_uri が URL エンコードされている
        assert "http%3A%2F%2Flocalhost" in url

    def test_login_uses_callback_port_from_server(self, monkeypatch):
        captured = {}

        fake_server = MagicMock()
        fake_server.server_address = ("localhost", 9999)
        fake_server.serve_forever = lambda: None
        fake_server.__enter__ = MagicMock(return_value=fake_server)
        fake_server.__exit__ = MagicMock(return_value=False)

        server_cls = MagicMock(return_value=fake_server)
        monkeypatch.setattr(
            "public_database_login.ThreadingHTTPServer", server_cls)

        def capture_open(url):
            captured["url"] = url
        monkeypatch.setattr(
            "public_database_login.webbrowser.open", capture_open)

        login("http://example.com")
        assert "9999" in captured["url"]

    def test_login_resets_auth_token(self, monkeypatch):
        public_database_login.auth_token = "OLD"
        self._patch_server(monkeypatch, serve_forever=lambda: None)
        result = login("http://example.com")
        assert result is None