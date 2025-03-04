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
from typing import Any, List

from nicegui import ui

from browser import Browser

# 創建 log 資料夾（如果不存在）
os.makedirs("log", exist_ok=True)
# 創建 local 資料夾（如果不存在）
os.makedirs("local", exist_ok=True)

# 設定日誌
log_filename = os.path.join("log", f"ilearning_cheater_{datetime.now().strftime('%Y%m%d')}.log")
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


def run_nicegui(command_queue: Queue, credentials_queue: Queue, questions_queue: Queue):
    ui.label("iLearning Cheater").classes("text-h3 font-bold")

    @ui.page("/")
    def main_page():
        # 在這裡定義 expansions
        expansions: List[Any] = []

        with ui.grid(columns=2).classes("gap-4 w-full"):
            # 左半邊：登入和單一測驗
            with ui.column().classes("gap-4"):
                # 帳密區域
                with ui.card().classes("w-full"):
                    with ui.expansion("登入資訊", value=True).classes("w-full"):
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
                            on_click=lambda: credentials_queue.put((account.value, password.value)),
                        )

                # 控制按鈕
                with ui.card().classes("w-full"):
                    ui.label("操作").classes("text-h6")
                    ui.button(
                        text="開始/繼續測驗",
                        on_click=lambda: command_queue.put(("start_continue_exam", None)),
                    )
                    ui.button(
                        text="自動作答目前頁面（興通識 Online 等單頁單題不打亂適用）",
                        on_click=lambda: command_queue.put(("take_exam", None)),
                    )
                    ui.button(
                        text="手動作答目前頁面（取得解答）",
                        on_click=lambda: command_queue.put(("manual_take_exam", None)),
                    )

                # 題目顯示區域
                with ui.card().classes("w-full"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("題目資訊").classes("text-h6")
                        with ui.row().classes("gap-2"):
                            ui.button("全部展開", on_click=lambda: [exp.set_value(True) for exp in expansions])
                            ui.button("全部折疊", on_click=lambda: [exp.set_value(False) for exp in expansions])
                    questions_container = ui.column().classes("w-full gap-2")

            # 右半邊：多個測驗網址
            with ui.card().classes("w-full"):
                ui.label("批次自動作答").classes("text-h6")
                url_container = ui.column().classes("w-full gap-2")
                url_rows: List[ui.row] = []
                url_inputs: List[ui.input] = []

                def create_url_row(index: int):
                    row = ui.row().classes("w-full items-center gap-2")
                    url_rows.append(row)
                    with row:
                        url_input = ui.input(
                            label=f"網址 {index + 1}",
                            placeholder="請輸入測驗網址",
                        ).classes("flex-grow")
                        url_inputs.append(url_input)

                        def remove_url():
                            idx = url_rows.index(row)
                            url_inputs.pop(idx)
                            url_rows.pop(idx)
                            row.delete()
                            # 重新編號
                            for i, inp in enumerate(url_inputs):
                                inp.props(f'label="網址 {i + 1}"')

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
                        command_queue.put(("take_exams", valid_urls))

                with ui.row():
                    ui.button("新增網址", on_click=add_url_input)
                    ui.button("開始自動作答多個測驗（興通識 Online 等單頁單題不打亂適用）", on_click=submit_urls)

                # 預設新增一個網址輸入框
                add_url_input()

        def check_questions():
            nonlocal expansions  # 聲明使用外部的 expansions 變數
            try:
                questions = questions_queue.get_nowait()
                logging.info(f"GUI received {len(questions)} questions")

                # 清除舊的題目
                with questions_container:
                    questions_container.clear()
                    logging.info("Cleared old questions")

                # 顯示通知
                ui.notify(f"已取得 {len(questions)} 個題目")

                # 清空並重新儲存所有的 expansion 元件
                expansions.clear()

                # 顯示新的題目
                for i, q in enumerate(questions, 1):
                    with questions_container:
                        # 準備標題文字：題號 + 前20個字 + 答案
                        title_preview = q.title[:20] + ("..." if len(q.title) > 20 else "")
                        answer_preview = f"（答案：{', '.join(q.answer_text)}）"
                        expansion_title = f"題目 {i}：{title_preview} {answer_preview}"

                        # 創建 expansion 並儲存起來
                        exp = ui.expansion(expansion_title, value=True).classes("w-full")
                        expansions.append(exp)

                        with exp:
                            ui.label(f"題目：{q.title}").classes("text-lg font-bold mb-2")  # 加大字體並加粗
                            ui.label("答案：").classes("text-lg text-green-600 font-bold")  # 答案標題
                            ui.label(f"{', '.join(q.answer_text)}").classes("text-lg text-green-600 mb-2")  # 答案內容
                            ui.label("選項：").classes("text-lg font-bold")  # 選項標題
                            with ui.column().classes("gap-1 ml-4"):  # 使用 column 來垂直排列選項，並加入左邊距
                                for option in q.options:
                                    is_correct = option in q.answer_text
                                    ui.label(f"• {option}").classes(
                                        "text-green-600 font-bold" if is_correct else "text-gray-700"
                                    )
                            logging.info(f"Added question {i} to GUI")

                # 強制更新 UI
                ui.update()
                logging.info("UI update completed")
            except Empty:
                pass
            except Exception as e:
                logging.error(f"Error in check_questions: {str(e)}")
                ui.notify(f"顯示題目時發生錯誤：{str(e)}", type="negative")

        # 增加檢查頻率
        ui.timer(0.05, check_questions)

    ui.run(
        title="iLearning Cheater",
        reload=False,
        port=find_free_port(),
    )


def run_selenium(command_queue: Queue, credentials_queue: Queue, questions_queue: Queue):
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
                account, password = credentials_queue.get_nowait()
                logging.info(f"Logging in with account: {account}")
                browser.login(account, password)
            except Empty:
                pass  # Queue 為空是正常的，不需要記錄
            except Exception as e:
                logging.error(f"Error during login: {str(e)}")

            try:
                # 檢查命令
                command, urls = command_queue.get_nowait()
                if command == "take_exam":
                    logging.info("Starting exam on current page")
                    browser.auto_take_exam()
                elif command == "manual_take_exam":
                    logging.info("Starting manual exam on current page")
                    questions = browser.manually_take_exam()
                    logging.info(f"Got {len(questions)} questions")
                    questions_queue.put(questions)
                elif command == "take_exams":
                    for url in urls:
                        logging.info(f"Processing exam at URL: {url}")
                        browser.auto_take_exam(url)
                elif command == "start_continue_exam":
                    logging.info("Starting/continuing exam on current page")
                    browser.start_continue_exam()
            except Empty:
                pass  # Queue 為空是正常的，不需要記錄
            except Exception as e:
                logging.error(f"Error during exam taking: {str(e)}")

            # 短暫休息以減少 CPU 使用率
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, cleaning up...")
        cleanup()
        sys.exit(0)


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    logging.info("Starting iLearning Cheater")

    command_queue: Queue = Queue()
    credentials_queue: Queue = Queue()
    questions_queue: Queue = Queue()
    selenium_process = Process(target=run_selenium, args=(command_queue, credentials_queue, questions_queue))

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
    run_nicegui(command_queue, credentials_queue, questions_queue)
    selenium_process.join()
