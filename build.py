import os
from pathlib import Path

import PyInstaller.__main__

# 獲取虛擬環境的套件路徑
PACKAGES_DIR = Path(".venv") / "Lib" / "site-packages"

# 確保輸出目錄存在
os.makedirs("dist", exist_ok=True)

# 創建必要的資料夾
os.makedirs("local", exist_ok=True)

# 打包參數
options = [
    "src/main.py",  # 主程式
    "--name=iLearning-Cheater",  # 輸出檔名
    "--clean",  # 清理暫存
    f"--add-data={PACKAGES_DIR / 'ddddocr'};ddddocr",  # ddddocr 及其模型
    f"--add-data={PACKAGES_DIR / 'nicegui'};nicegui",  # nicegui 及其靜態檔案
    f"--add-data={PACKAGES_DIR / 'bs4'};bs4",  # BeautifulSoup4 及其資源
    "--collect-all=nicegui",
    "--collect-all=ddddocr",
    "--collect-all=onnxruntime",
    "--collect-all=bs4",  # 收集所有 bs4 相關文件
]

# 執行打包
PyInstaller.__main__.run(options)

print("打包完成！檢查 dist 資料夾中的執行檔。")
