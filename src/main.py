import atexit
import logging
import os
import signal
import socket
import sys
import time
from datetime import datetime
from multiprocessing import Process, Queue
from queue import Empty
from typing import List

from nicegui import ui

from browser import Browser

# 創建 log 資料夾（如果不存在）
os.makedirs("log", exist_ok=True)
# 創建 local 資料夾（如果不存在）
os.makedirs("local", exist_ok=True)

# 設定日誌
log_filename = os.path.join("log", f"ilearning_ppt_downloader_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def run_nicegui(command_queue: Queue, credentials_queue: Queue, status_queue: Queue):
    ui.label("iLearning PPT 下載器").classes("text-h3 font-bold")

    @ui.page("/")
    def main_page():
        with ui.grid(columns=2).classes("gap-4 w-full"):
            # 左半邊：登入資訊
            with ui.column().classes("gap-4"):
                # 帳密區域
                with ui.card().classes("w-full"):
                    with ui.expansion("登入資訊", value=True).classes("w-full"):
                        login_url = ui.input(
                            label="iLearning 網站網址",
                            placeholder="https://lms2020.nchu.edu.tw/",
                            value="https://lms2020.nchu.edu.tw/",
                            validation={"不應包含空白": lambda value: " " not in value},
                        )
                        account = ui.input(
                            label="請輸入學號",
                            placeholder="請輸入學號",
                            validation={"不應包含空白": lambda value: " " not in value},
                        )
                        password = ui.input(
                            label="請輸入密碼",
                            placeholder="請輸入密碼",
                            password=True,
                            validation={"不應包含空白": lambda value: " " not in value},
                        )
                        ui.button(
                            "登入",
                            on_click=lambda: credentials_queue.put((login_url.value, account.value, password.value)),
                        )

            # 右半邊：投影片下載
            with ui.column().classes("gap-4"):
                with ui.card().classes("w-full"):
                    ui.label("投影片下載").classes("text-h6")
                    url_container = ui.column().classes("w-full gap-2")
                    url_rows: List[ui.row] = []
                    url_inputs: List[ui.input] = []

                    def create_url_row(index: int):
                        row = ui.row().classes("w-full items-center gap-2")
                        url_rows.append(row)
                        with row:
                            url_input = ui.input(
                                label=f"投影片網址 {index + 1}",
                                placeholder="請輸入投影片網址",
                            ).classes("flex-grow whitespace-pre-wrap break-all")
                            url_inputs.append(url_input)

                            def remove_url():
                                idx = url_rows.index(row)
                                url_inputs.pop(idx)
                                url_rows.pop(idx)
                                row.delete()
                                # 重新編號
                                for i, inp in enumerate(url_inputs):
                                    inp.props(f'label="投影片網址 {i + 1}"')

                            ui.button(
                                icon="delete",
                                on_click=remove_url,
                                color="red",
                            ).classes("min-w-8 w-8 h-8")

                    def add_url_input():
                        with url_container:
                            create_url_row(len(url_inputs))

                    def submit_urls():
                        valid_urls = [url.value for url in url_inputs if url.value]
                        if valid_urls:
                            command_queue.put(("download_slides", valid_urls))

                    with ui.row():
                        ui.button("新增網址", on_click=add_url_input)
                        ui.button("開始下載投影片", on_click=submit_urls)

                    # 預設新增一個網址輸入框
                    add_url_input()

                # 狀態顯示區域
                with ui.card().classes("w-full"):
                    ui.label("下載狀態").classes("text-h6")
                    status_container = ui.column().classes("w-full gap-2")

                    # 新增進度條
                    progress_bar = ui.linear_progress().classes("w-full")
                    progress_bar.props('color="primary"')
                    progress_bar.visible = False
                    progress_text = ui.label().classes("text-sm text-gray-600 text-center w-full")
                    progress_text.visible = False

                    # 新增當前下載的簡報名稱
                    current_slide_label = ui.label().classes("text-lg font-bold")
                    current_slide_label.visible = False

                    # 新增詳細狀態訊息
                    status_label = ui.label().classes("text-body1")
                    status_label.visible = False

        def check_status():
            try:
                status = status_queue.get_nowait()
                with status_container:
                    # 解析狀態訊息
                    if status.startswith("開始下載簡報："):
                        current_slide_label.text = status
                        current_slide_label.visible = True
                        progress_bar.visible = True
                        progress_text.visible = True
                        status_label.visible = True
                        progress_bar.set_value(0)
                        progress_text.text = "0%"
                    elif status.startswith("下載進度："):
                        # 從進度訊息中提取百分比
                        try:
                            percent = float(status.split("(")[1].split("%")[0])
                            progress_bar.set_value(percent / 100)
                            progress_text.text = f"{int(percent)}%"
                            status_label.text = status
                        except (ValueError, IndexError):
                            status_label.text = status
                    elif status.startswith("簡報下載完成："):
                        current_slide_label.text = status
                        status_label.text = "下載完成！"
                        progress_bar.set_value(1)
                        progress_text.text = "100%"
                    elif status.startswith("PDF 檔案生成失敗："):
                        current_slide_label.text = status
                        status_label.text = "PDF 生成失敗！"
                        progress_bar.set_value(0)
                        progress_text.text = "0%"
                    else:
                        status_label.text = status
                        status_label.visible = True

                ui.update()
            except Empty:
                pass
            except Exception as e:
                logging.error(f"Error in check_status: {str(e)}")
                ui.notify(f"更新狀態時發生錯誤：{str(e)}", type="negative")

        # 增加檢查頻率
        ui.timer(0.05, check_status)

    ui.run(
        title="iLearning PPT 下載器",
        reload=False,
        port=find_free_port(),
    )


def run_selenium(command_queue: Queue, credentials_queue: Queue, status_queue: Queue):
    browser = Browser()

    def cleanup():
        try:
            browser.driver.quit()
        except Exception as e:
            logging.error(f"Error during browser cleanup: {str(e)}")

    atexit.register(cleanup)

    try:
        while True:
            try:
                # 檢查瀏覽器是否已被關閉
                try:
                    if not browser.driver.window_handles:
                        logging.info("Browser has been closed, exiting...")
                        cleanup()
                        os._exit(0)
                except Exception:
                    logging.info("Browser has been closed, exiting...")
                    cleanup()
                    os._exit(0)

                # 檢查登入資訊
                login_url, account, password = credentials_queue.get_nowait()
                logging.info(f"Logging in with account: {account} at {login_url}")
                browser.login_url = login_url
                if browser.login(account, password):
                    status_queue.put("登入成功")
                else:
                    status_queue.put("登入失敗，請重新再試")
            except Empty:
                pass  # Queue 為空是正常的，不需要記錄
            except Exception as e:
                logging.error(f"Error during login: {str(e)}")
                status_queue.put(f"登入失敗：{str(e)}")

            try:
                # 檢查命令
                command, urls = command_queue.get_nowait()
                if command == "download_slides":
                    for url in urls:
                        logging.info(f"Processing slides at URL: {url}")
                        status_queue.put(f"正在下載投影片：{url}")
                        if browser.get_slides(url, status_queue.put):
                            status_queue.put(f"成功下載投影片：{url}")
                        else:
                            status_queue.put(f"下載投影片失敗：{url}")
            except Empty:
                pass  # Queue 為空是正常的，不需要記錄
            except Exception as e:
                logging.error(f"Error during slides download: {str(e)}")
                status_queue.put(f"下載投影片時發生錯誤：{str(e)}")

            # 短暫休息以減少 CPU 使用率
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, cleaning up...")
        cleanup()
        sys.exit(0)


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    logging.info("Starting iLearning PPT Downloader")

    command_queue: Queue = Queue()
    credentials_queue: Queue = Queue()
    status_queue: Queue = Queue()
    selenium_process = Process(target=run_selenium, args=(command_queue, credentials_queue, status_queue))

    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, cleaning up...")
        selenium_process.terminate()
        selenium_process.join()
        sys.exit(0)

    # System signal handler
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    def cleanup():
        if selenium_process.is_alive():
            logging.info("Cleaning up selenium process...")
            selenium_process.terminate()
            selenium_process.join()

    atexit.register(cleanup)

    selenium_process.start()
    run_nicegui(command_queue, credentials_queue, status_queue)
    selenium_process.join()
