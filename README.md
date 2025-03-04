# iLearning PPT Downloader
A selenium web scraper for iLearning with NiceGUI.

# How to use
1. 從 Release 下載 `.zip` 檔案（或是自己 Build）
2. 打開 `ilearning-ppt-downloader.exe`
3. 等待 NiceGUI 管理介面及一個 Selenium 瀏覽器自己打開

![介面示意圖](/static/screenshot_介面示意.png)

4. 從 NiceGUI 輸入帳號密碼登入，如果出現錯誤可能是驗證碼判斷錯誤，請重新再登入一次即可
5. 開始使用！你可以在複製簡報網址以後輸入右下的「下載簡報」區

![簡報網址示意圖](/static/screenshot_簡報網址.png)

# Feature
- Support platform that similar to ilearning. (You can change the URL whatever you want)
- NiceGUI

# Packing
Using Pyinstaller.

You can run `pdm run build.py`, the args is set in `build.py`.