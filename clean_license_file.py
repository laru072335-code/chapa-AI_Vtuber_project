"""
ライセンスファイルに記載されたそれぞれのライブラリのライセンスファイルの絶対パスの表示を相対パスの表示にするもの。
pixi licenseにて実行される
"""
import os

def main():
    target_file = "LICENSE.txt"
    if not os.path.exists(target_file):
        print(f"Error: {target_file} not found.")
        return

    current_dir = os.getcwd() + os.sep
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    cleaned_content = content.replace(current_dir, "")
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(cleaned_content)
    
    print(f"Successfully cleaned paths in {target_file}")

if __name__ == "__main__":
    main()
