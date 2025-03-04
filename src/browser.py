import os
import time
from typing import List

import ddddocr
import requests
from bs4 import BeautifulSoup
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


class Browser:
    def __init__(self, headless: bool = False, login_url: str = "https://lms2020.nchu.edu.tw/"):
        self.headless = headless
        self.login_url = login_url
        self.ocr = ddddocr.DdddOcr()

        # 創建 Chrome 瀏覽器
        service = Service()
        options = webdriver.ChromeOptions()

        # 讓網頁不知道我們在自動控制
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # 讓網頁不知道我們有切換頁面或在背景執行
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")

        # 關閉「保存密碼」
        options.add_experimental_option(
            "prefs",
            {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
            },
        )

        # Headless: 不開啟 GUI
        if self.headless:
            options.add_argument("--headless")

        self.driver = webdriver.Chrome(service=service, options=options)
        self.session = requests.Session()

    def login(self, account: str, password: str):
        self.account = account
        self.password = password

        self.driver.get(self.login_url)

        # 輸入帳號
        account_input_field = self.driver.find_element(By.NAME, "account")
        account_input_field.clear()
        account_input_field.send_keys(self.account)

        # 輸入密碼
        password_input_field = self.driver.find_element(By.NAME, "password")
        password_input_field.clear()
        password_input_field.send_keys(self.password)

        # 輸入驗證碼
        captcha = self.get_captcha()
        captcha_input_field = self.driver.find_element(By.NAME, "captcha")
        captcha_input_field.clear()
        captcha_input_field.send_keys(captcha)

        # 登入
        login_button = self.driver.find_element(By.CLASS_NAME, "btn-text")
        login_button.click()

        time.sleep(2)
        return self.is_login()

    def is_login(self):
        try:
            # 有登入鍵代表目前未登入
            self.driver.find_element(By.LINK_TEXT, "登入")
            return False
        except NoSuchElementException:
            return True
        except Exception as e:
            print(e)
            return False

    def get_captcha(self):
        # 確保有 local 資料夾
        os.makedirs("./local", exist_ok=True)

        captcha_image = self.driver.find_element(By.CLASS_NAME, "js-captcha")
        captcha_image.screenshot("./local/captcha.png")

        with open("./local/captcha.png", "rb") as f:
            image = f.read()
        captcha = str(self.ocr.classification(image))
        return captcha

    def get_slides(self, url: str, status_callback=None):
        self.driver.get(url)
        source = self.driver.page_source

        soup = BeautifulSoup(source, "html.parser")

        # 尋找 classname 為 slide 的元素
        slides = soup.find_all(class_="slide")

        images = [slide.find("img")["src"] for slide in slides]
        full_urls = [f"{self.login_url.removesuffix('/')}/{image.removeprefix('/')}" for image in images]

        try:
            slide_name = soup.find(class_="title").text.strip()  # pyright: ignore
        except AttributeError:
            if status_callback:
                status_callback("無法取得簡報名稱")
            return False

        if status_callback:
            status_callback(f"開始下載簡報：{slide_name}")

        os.makedirs(f"slides/{slide_name}", exist_ok=True)

        # 儲存所有下載的圖片路徑
        downloaded_images = []
        total_slides = len(full_urls)

        for i, image_url in enumerate(full_urls):
            image_path = f"slides/{slide_name}/{image_url.split('/')[-1]}"
            response = self.session.get(image_url)
            with open(image_path, "wb") as f:
                f.write(response.content)

            downloaded_images.append(image_path)
            if status_callback:
                status_callback(f"下載進度：{i + 1}/{total_slides} ({((i + 1) / total_slides * 100):.0f}%)")

        # 生成 PDF 檔案
        if status_callback:
            status_callback("正在生成 PDF 檔案...")
        pdf_path = f"slides/{slide_name}/簡報.pdf"
        if self.image_to_pdf(downloaded_images, pdf_path):
            if status_callback:
                status_callback(f"簡報下載完成：{slide_name}")
            return True
        else:
            if status_callback:
                status_callback(f"PDF 檔案生成失敗：{slide_name}")
            return False

    def image_to_pdf(self, image_paths: List[str], output_path: str) -> bool:
        """將多張圖片轉換為 PDF 檔案

        Args:
            image_paths: 圖片路徑列表
            output_path: 輸出的 PDF 檔案路徑

        Returns:
            bool: 是否成功轉換
        """
        try:
            # 創建 PDF 文件
            c = canvas.Canvas(output_path, pagesize=A4)

            # A4 紙張尺寸（單位：點）
            page_width, page_height = A4
            # 設定邊距
            margin = 40
            # 可用區域
            available_width = page_width - (margin * 2)
            available_height = page_height - (margin * 2)

            for image_path in image_paths:
                # 打開圖片
                img = Image.open(image_path)

                # 獲取圖片尺寸
                img_width, img_height = img.size

                # 計算縮放比例
                width_ratio = available_width / img_width
                height_ratio = available_height / img_height
                # 使用較小的比例，確保圖片完整顯示
                scale = min(width_ratio, height_ratio)

                # 計算縮放後的尺寸
                scaled_width = img_width * scale
                scaled_height = img_height * scale

                # 計算置中位置
                x = (page_width - scaled_width) / 2
                y = (page_height - scaled_height) / 2

                # 將圖片繪製到 PDF
                c.drawImage(image_path, x, y, width=scaled_width, height=scaled_height)
                c.showPage()

            # 保存 PDF
            c.save()
            return True

        except Exception as e:
            print(f"轉換 PDF 時發生錯誤: {e}")
            return False
