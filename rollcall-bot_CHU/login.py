import json
import os
import time
from typing import Tuple
from rich import print
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from config import load_config

COOKIE_FILE = "cookies.json"

def save_cookies(cookies, path=COOKIE_FILE):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_cookies(path=COOKIE_FILE):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class SessionDriver:
    """
    轻量“驱动”适配器，使用 requests.Session 模拟需要的接口。
    提供:
      - get_cookies() -> list[dict(name, value)]
      - execute_async_script(script, url) -> dict(status, ok, text) 或 {error: ...}
    """
    def __init__(self, session: requests.Session):
        self.session = session

    def get_cookies(self):
        return [{"name": c.name, "value": c.value} for c in self.session.cookies]

    def execute_async_script(self, script, url, timeout=15):
        try:
            resp = self.session.get(url, timeout=timeout)
            return {"status": resp.status_code, "ok": resp.ok, "text": resp.text}
        except Exception as e:
            return {"error": str(e)}


def load_session_from_cookies(cookies_list):
    s = requests.Session()
    for c in cookies_list:
        name = c.get("name")
        value = c.get("value")
        domain = c.get("domain", None)
        path = c.get("path", "/")
        if domain:
            s.cookies.set(name, value, domain=domain, path=path)
        else:
            s.cookies.set(name, value, path=path)
    return s


def login() -> Tuple[SessionDriver, dict]:
    from main import ver

    print(f"CHU-TronClassTool {ver}\ntransplanted by Rinn")
    print("=================")

    print('正在初始化...', end='')
    config = load_config()

    username = config.get("username", '') or ''
    password = config.get("password", '') or ''
    base_url = config["base_url"]
    interval = config["interval"]
    driver_path = config["driver"]

    print('完成')
    print(f"当前配置: \n平台地址: {base_url} \n轮询间隔: {interval}秒")
    print("=================")

    api_url = f"{base_url}/api/radar/rollcalls"

    raw_cookies = load_cookies()
    if raw_cookies:
        session = load_session_from_cookies(raw_cookies)
        try:
            resp = session.get(api_url, timeout=10)
            if resp.status_code == 200:
                text = resp.text or ""
                login_keywords = ["统一身份认证平台", "请登录", "login"]
                if any(k in text for k in login_keywords):
                    print("登录态已失效，将重新登录")
                else:
                    print("已恢复登录态")
                    return SessionDriver(session), config
            else:
                print(f"登录态恢复失败-{resp.status_code}，将重新登录")
        except Exception as e:
            print(f"登录态恢复失败，将重新登录: {e}")

    print("唤起浏览器登录...")
    chrome_options = Options()
    try:
        driver = webdriver.Chrome(options=chrome_options, service=Service(driver_path))
    except ValueError as ve:
        print(f"找不到浏览器文件。\n{ve}")
        exit(0)
    except Exception as e:
        print(f"唤起浏览器失败。\n{e}")
        exit(0)

    print("连接 TronClass...", end='')
    driver.get(f"{base_url}/user/index#/")
    try:
        WebDriverWait(driver, 10, 0.5).until(EC.title_contains("统一身份认证平台"))
        print("成功")
    except Exception as e:
        print(f"失败\n{e}")
        driver.quit()
        exit(0)

    if bool(username and password):
        time.sleep(2)
        print('正在自动登录...')
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)

        has_captcha = bool(driver.find_elements(By.ID, "captcha"))

        if not has_captcha:
            driver.find_element(By.ID, "login_submit").click()
            WebDriverWait(driver, 15, 0.5).until(
                lambda d: ("首页 - 畅课" in d.title) or d.find_elements(By.ID, "showErrorTip")
            )
        else:
            print("需要验证码，请在浏览器中输入并完成登录...")
            WebDriverWait(driver, timeout=3600, poll_frequency=0.5).until(
                lambda d: ("首页 - 畅课" in d.title) or d.find_elements(By.ID, "showErrorTip")
            )

    else:
        print("请手动完成登录...")
        WebDriverWait(driver, timeout=3600, poll_frequency=0.5).until(
            lambda d: ("首页 - 畅课" in d.title) or d.find_elements(By.ID, "showErrorTip")
        )


    if driver.find_elements(By.ID, "showErrorTip"):
        error_tips = driver.find_elements(By.ID, "showErrorTip")
        print(f"登录失败-{error_tips[0].text}\n五秒后程序退出")
        driver.quit()
        time.sleep(5)
        exit(0)

    user_name = driver.find_element(By.ID, 'userCurrentName').text if driver.find_elements(By.ID, 'userCurrentName') else "Unknown"
    print(f"用户 {user_name} 登录成功")

    cookies = driver.get_cookies()
    save_cookies(cookies)
    session = load_session_from_cookies(cookies)

    driver.quit()
    time.sleep(interval)
    return SessionDriver(session), config
