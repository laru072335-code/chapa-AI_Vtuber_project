"""
エラーをしっかりキャッチするためのプログラム
"""
import sys
import traceback

def run_with_error_handling(func, *args, **kwargs):
    """
    別スレッドで実行される関数をラップし、例外発生時にトレースバックを標準エラー出力に出力して再送出する。
    別スレッド実行時にエラーがぬりつぶされるのを防止する。
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        func_name = getattr(func, "__name__", str(func))
        print(f"[database_utilities] 別スレッド実行時エラー ({func_name}): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise
