import os
import subprocess
from pathlib import Path


def build_with_pyinstaller():
    # 獲取當前目錄
    current_dir = Path(__file__).parent.absolute()

    # 設定要編譯的 Python 檔案
    main_file = str(current_dir / "src" / "main.py")

    # 設定輸出目錄
    output_dir = str(current_dir / "dist")

    # 獲取 PDM 虛擬環境的 Python 路徑
    venv_python = os.path.join(current_dir, ".venv", "Scripts", "python.exe")

    # PyInstaller 編譯命令
    pyinstaller_command = [
        venv_python,
        "-m",
        "PyInstaller",
        "--name=ilearning-ptt-downloader",
        "--clean",
        f"--distpath={output_dir}",
        "--add-data=src;src",
        "--collect-all=nicegui",
        "--collect-all=ddddocr",
        # 包含必要的套件
        "--hidden-import=selenium",
        "--hidden-import=ddddocr",
        "--hidden-import=nicegui",
        "--hidden-import=bs4",
        "--hidden-import=PIL",
        "--hidden-import=reportlab",
        main_file,
    ]

    # 執行編譯命令
    try:
        subprocess.run(pyinstaller_command, check=True)
        print("編譯成功！")
    except subprocess.CalledProcessError as e:
        print(f"編譯失敗：{e}")


if __name__ == "__main__":
    build_with_pyinstaller()
