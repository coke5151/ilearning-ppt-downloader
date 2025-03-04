import os
import subprocess
from pathlib import Path


def build_with_nuitka():
    # 獲取當前目錄
    current_dir = Path(__file__).parent.absolute()

    # 設定要編譯的 Python 檔案
    main_file = str(current_dir / "src" / "main.py")

    # 設定輸出目錄
    output_dir = str(current_dir / "dist")

    # 獲取 PDM 虛擬環境的 Python 路徑
    venv_python = os.path.join(current_dir, ".venv", "Scripts", "python.exe")

    # Nuitka 編譯命令
    nuitka_command = [
        venv_python,
        "-m",
        "nuitka",
        "--output-filename=ilearning-ptt-downloader",
        "--standalone",
        "--nofollow-imports",
        "--remove-output",
        "--no-pyi-file",
        "--assume-yes-for-downloads",
        f"--output-dir={output_dir}",
        "--include-module=pywin32_bootstrap",
        # 包含必要的套件
        "--include-package=selenium",
        "--include-package=ddddocr",
        "--include-package=nicegui",
        "--include-package=bs4",
        "--include-package=PIL",
        "--include-package=reportlab",
        main_file,
    ]

    # 執行編譯命令
    try:
        subprocess.run(nuitka_command, check=True)
        print("編譯成功！")
    except subprocess.CalledProcessError as e:
        print(f"編譯失敗：{e}")


if __name__ == "__main__":
    build_with_nuitka()
