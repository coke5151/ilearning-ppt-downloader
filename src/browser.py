import os
import time

import ddddocr
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

LOGIN_URL = "https://lms2020.nchu.edu.tw/"


class Browser:
    def __init__(self, headless: bool = False):
        self.headless = headless
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

        self.driver.get(LOGIN_URL)

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

    def get_slides(self, url: str):
        self.driver.get(url)
        source = self.driver.page_source

        soup = BeautifulSoup(source, "html.parser")

        # 尋找 classname 為 slide 的元素
        slides = soup.find_all(class_="slide")

        images = [slide.find("img")["src"] for slide in slides]
        full_urls = [f"{LOGIN_URL.removesuffix('/')}/{image.removeprefix('/')}" for image in images]

        try:
            slide_name = soup.find(class_="title").text.strip()  # type: ignore
        except AttributeError:
            return False

        os.makedirs(f"slides/{slide_name}", exist_ok=True)

        for i, image_url in enumerate(full_urls):
            response = self.session.get(image_url)
            with open(f"slides/{slide_name}/{image_url.split('/')[-1]}", "wb") as f:
                f.write(response.content)

            print(f"Downloaded {i + 1}/{len(full_urls)} images")

        return True
