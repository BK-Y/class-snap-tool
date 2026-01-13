# start.py
import os
import sys
import subprocess

def main():
    # 获取当前目录下的 .venv
    venv_path = os.path.join(os.path.dirname(__file__), '.venv')
    
    if not os.path.exists(venv_path):
        print("❌ 错误：未找到 .venv 目录")
        return

    # 构建 Python 可执行路径
    if sys.platform == "win32":
        python_executable = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        python_executable = os.path.join(venv_path, "bin", "python")

    # 启动 app.py
    cmd = [python_executable, "app.py"]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()
