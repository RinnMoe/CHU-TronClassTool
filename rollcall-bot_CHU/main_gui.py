# CHU-TronClassTool-GUI 0.1.1
# transplant by Rinn
# origin repository https://github.com/KrsMt-0113/XMU-Rollcall-Bot

import sys
import time
import json
import uuid
import requests
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.ie.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from parse_rollcalls import parse_rollcalls
from gui import MainWindow


class WorkerSignals(QObject):
    """工作线程信号"""
    log = pyqtSignal(str, str)  # message, level
    status = pyqtSignal(str)
    qr_code = pyqtSignal(str)  # image path
    hide_qr = pyqtSignal()
    started = pyqtSignal()
    finished = pyqtSignal()
    check_increment = pyqtSignal()
    sign_increment = pyqtSignal()


class MonitorWorker(QThread):
    """监测工作线程"""

    def __init__(self, username, password, sendkey):
        super().__init__()
        self.username = username
        self.password = password
        self.sendkey = sendkey
        self.signals = WorkerSignals()
        self.running = True
        self.driver = None

    def log(self, message, level="info"):
        """发送日志信号"""
        self.signals.log.emit(message, level)

    def update_status(self, status):
        """更新状态"""
        self.signals.status.emit(status)

    def run(self):
        """运行监测任务"""
        try:
            # 签到列表获取接口，轮询间隔，轮询脚本
            api_url = "https://course-online.chd.edu.cn/api/radar/rollcalls"
            fetch_script = """
const url = arguments[0];
const callback = arguments[arguments.length - 1];
fetch(url, {credentials: 'include'})
  .then(resp => resp.text().then(text => callback({status: resp.status, ok: resp.ok, text: text})))
  .catch(err => callback({error: String(err)}));
"""

            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头运行

            # 启动selenium
            self.log("初始化 Selenium...", "info")
            self.update_status("初始化...")
            self.driver = webdriver.Chrome(chrome_options, service=Service('chromedriver.exe'))

            # 访问登录页面
            self.driver.get("https://course-online.chd.edu.cn/user/index#/")
            self.log("已连接 TronClass", "success")

            WebDriverWait(self.driver, 10, 0.5).until(EC.title_contains('统一身份认证平台'))
            self.driver.find_element(By.ID, "username").send_keys(self.username)
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            self.driver.find_element(By.ID, "login_submit").click()
            self.log("登录中...", "info")

            # 验证登录
            WebDriverWait(self.driver, 100, 0.5).until(EC.title_contains('首页 - 畅课'))
            res = requests.get(api_url, cookies={c['name']: c['value'] for c in self.driver.get_cookies()})
            if res.status_code == 200:
                self.log(f'用户 {self.driver.find_element(By.ID, "userCurrentName").text} 已登录成功', "success")
                # sc_send(self.sendkey, "签到机器人", "登录成功！五秒后进入监测模式...", {"tags": "签到机器人"})
            else:
                self.log("登录失败.", "error")
                return

            self.log("5秒后开始监测", "info")
            self.log(f"轮询间隔为 {interval} 秒", "info")
            time.sleep(5)

            deviceID = uuid.uuid4()
            self.log("监测已启动~", "success")
            self.update_status("运行中...")
            # sc_send(self.sendkey, "签到机器人", "签到监测已启动。", {"tags": "签到机器人"})
            self.signals.started.emit()

            temp_data = {'rollcalls': []}
            check_count = 0

            while self.running:
                res = self.driver.execute_async_script(fetch_script, api_url)
                check_count += 1

                # if check_count % 10 == 0:  # 每10次检测更新一次计数
                self.signals.check_increment.emit()

                if res['status'] == 200:
                    text = res.get('text', '')
                    try:
                        data = json.loads(text)
                        if temp_data == data:
                            time.sleep(interval)
                            continue
                        else:
                            temp_data = data
                            if len(temp_data['rollcalls']) > 0:
                                self.log(f"发现 {len(temp_data['rollcalls'])} 个新签到！", "warning")
                                self.signals.sign_increment.emit()

                                # 显示详细信息
                                for idx, rollcall in enumerate(temp_data['rollcalls']):
                                    self.log(f"签到: {idx+1}/{len(temp_data['rollcalls'])}: {rollcall['course_title']}", "info")
                                    self.log(f"  由 {rollcall['created_by_name']} 发起", "info")
                                    self.log(f"  状态: {rollcall['rollcall_status']}", "info")

                                if not parse_rollcalls(temp_data, self.driver):
                                    temp_data = {'rollcalls': []}
                                else:
                                    self.log("签到成功.", "success")
                    except Exception as e:
                        self.log(f"Error: {str(e)}", "error")

                elif res['status'] != 200:
                    self.log("连接断开，监测已终止。", "error")
                    # sc_send(self.sendkey, "签到机器人", "失去连接，监测已终止。", {"tags": "签到机器人"})
                    break
                time.sleep(interval)

        except Exception as e:
            self.log(f"Error: {str(e)}", "error")
        finally:
            if self.driver:
                self.driver.quit()
            self.signals.finished.emit()

    def stop(self):
        """停止监测"""
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def main():
    """主函数"""
    # 读取配置
    try:
        with open("config.json", encoding='utf-8') as f:
            config = json.load(f)
            username = config["username"]
            password = config["password"]
            global interval
            interval = config["interval"]
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return

    # 创建应用
    app = QApplication(sys.argv)

    # 创建主窗口
    window = MainWindow()

    # 创建工作线程
    worker = MonitorWorker(username, password, sendkey="")  # sendkey留空表示不发送通知

    # 连接信号
    worker.signals.log.connect(window.add_log)
    worker.signals.status.connect(window.update_status)
    # worker.signals.qr_code.connect(window.show_qr_code)
    # worker.signals.hide_qr.connect(window.hide_qr_code)
    worker.signals.started.connect(window.start_monitoring)
    worker.signals.finished.connect(window.stop_monitoring)
    worker.signals.check_increment.connect(window.increment_check_count)
    worker.signals.sign_increment.connect(window.increment_sign_count)

    # 连接停止按钮
    window.stop_button.clicked.connect(worker.stop)
    window.stop_button.clicked.connect(lambda: window.add_log("用户终止了监测.", "warning"))

    # 启动工作线程
    worker.start()

    # 显示窗口
    window.show()

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
