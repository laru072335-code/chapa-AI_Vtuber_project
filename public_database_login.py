"""
ネット上のDBにアクセスするためのログイン処理
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import threading

auth_token = None

class TimeoutHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_token
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        # 認証完了時
        if parsed_path.path == '/callback':
            if 'token' in query_params:
                auth_token = query_params['token'][0]
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                response_html = """
                <html>
                    <body style="text-align: center; font-family: sans-serif; padding-top: 50px;">
                        <h2>認証が完了しました！</h2>
                        <p>このウィンドウを閉じて、アプリに戻ってください。</p>
                        <script>window.close();</script>
                    </body>
                </html>
                """
                self.wfile.write(response_html.encode('utf-8'))
                
                # シャットダウンのトリガー
                threading.Thread(target=self.server.shutdown).start()
                return

        # 「ブラウザが閉じられた（またはキャンセルされた）」場合に明示的にサーバーへ教えるためのエンドポイント
        elif parsed_path.path == '/cancel':
            self.send_response(200)
            self.end_headers()
            threading.Thread(target=self.server.shutdown).start()
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        pass


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # タイムアウト時に呼び出されるメソッド
    def handle_timeout(self):
        print("\n[タイムアウト] 一定時間操作がなかったため、ログイン処理を中断します。")
        self.shutdown()


def login(url:str):
    global auth_token
    auth_token = None

    with ThreadingHTTPServer(("localhost", 0), TimeoutHTTPRequestHandler) as httpd:
        httpd.timeout = 60.0  # タイムアウト時間
        port = httpd.server_address[1]
        
        # 認証画面にキャンセル時のリンクや処理を組み込めるようにする
        redirect_uri = f"http://localhost:{port}/callback"
        # クエリ値なので "/" や ":" も含めて完全にエンコードする
        login_url = (f"{url}/login?redirect_uri="
                     f"{urllib.parse.quote(redirect_uri, safe='')}")

        print(f"ブラウザを開いて認証を行います（制限時間: 1分）: {login_url}")
        webbrowser.open(login_url)
        
        # サーバー稼働（タイムアウトまたはリクエスト完了で終了）
        httpd.serve_forever()

    return auth_token

if __name__ == '__main__':
    print("ログイン処理を開始します...")
    token = login()
    
    if token:
        print(f"\n[成功] 取得したトークン: {token}")
    else:
        print("\n[中断/失敗] ログインが完了しませんでした。")
