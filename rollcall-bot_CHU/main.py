# CHU-TronClassTool
ver = "0.2.1"

# transplanted by Rinn
# origin repository https://github.com/KrsMt-0113/XMU-Rollcall-Bot

import datetime
import time
import json
# import uuid
import requests
from rich import print
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.ie.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from parse_rollcalls import parse_rollcalls

def main():
    # 读取学号、密码、轮询间隔、经纬度
    try:
        with open("config.json", encoding='utf-8') as f:
            config = json.load(f)
            username = config["username"]
            password = config["password"]
            url = config["url"]
            interval = config["interval"]
            longitude = config["longitude"]
            latitude = config["latitude"]
            driver = config["driver"]
            run_headless = config["run_headless"]

    except (json.JSONDecodeError, FileNotFoundError):
        print("初次运行或配置文件损坏，正在生成配置文件 config.json，请填写相关信息后重新运行程序。")
        username = input('请输入您的学号: ')
        password = input('请输入您的密码: ')
        url = input('请输入 TronClass 平台地址 (默认 https://course-online.chd.edu.cn): ') or "https://course-online.chd.edu.cn"
        interval = input('请输入轮询间隔，单位秒 (默认 5): ') or 5
        longitude = input('请输入签到经度 (默认 113.000000): ') or 113.
        latitude = input('请输入签到纬度 (默认 28.000000): ') or 28.
        driver = input('请输入 ChromeDriver 路径 (默认 chromedriver.exe): ') or 'chromedriver.exe'
        run_headless = input('是否无头运行？(y/n, 默认 y): ') or 'y'
        config = {
            "username": username,
            "password": password,
            "url": url,
            "interval": int(interval),
            "longitude": float(longitude),
            "latitude": float(latitude),
            "driver": driver,
            "run_headless": True if run_headless.lower() == 'y' else False
        }
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    # 签到列表获取接口，轮询间隔，轮询脚本
    api_url = f"{url}/api/radar/rollcalls"
    fetch_script = """
    const url = arguments[0];
    const callback = arguments[arguments.length - 1];
    fetch(url, {credentials: 'include'})
      .then(resp => resp.text().then(text => callback({status: resp.status, ok: resp.ok, text: text})))
      .catch(err => callback({error: String(err)}));
    """

    chrome_options = Options()

    if run_headless:
        chrome_options.add_argument("--headless")  # 无头运行

    # 启动selenium
    print(f"CHU-TronClassTool {ver}\ntransplanted by Rinn\n正在初始化...")
    print(f"=================")
    print(f"当前配置: \n平台地址: {url} \n轮询间隔: {interval}秒")
    try:
        driver = webdriver.Chrome(chrome_options, service=Service("chromedriver.exe"))
    except ValueError as e:
        print(f"找不到浏览器文件。\n{e}")
        #todo: 下载 chromedriver
        exit()

    driver.get(f"{url}/user/index#/")
    print("已连接 TronClass\n登录中...")

    WebDriverWait(driver, 10, 0.5).until(EC.title_contains('统一身份认证平台'))
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login_submit").click()

    WebDriverWait(driver, 100, 0.5).until(EC.title_contains('首页 - 畅课'))
    print(f'用户 {driver.find_element(By.ID, "userCurrentName").text} 登录成功')

    res = requests.get(api_url, cookies={c['name']: c['value'] for c in driver.get_cookies()})
    if res.status_code == 200:
        print("五秒后进入监测...")
    else:
        print("登录失败。五秒后程序退出。")
        driver.quit()
        time.sleep(5)
        exit(0)

    time.sleep(5)

    print(f"签到监测启动。")

    temp_data = {'rollcalls': []}
    check_count = 0

    while True:
        try:
            res = driver.execute_async_script(fetch_script, api_url)
        except Exception as e:
            print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] 发生了错误-{e}')
            break

        check_count += 1

        if check_count % 5 == 0:
            print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] 监测已进行了{check_count}次')

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
                        if False in parse_rollcalls(temp_data, driver, longitude, latitude):
                            print(f"\n[{time.strftime('%H:%M:%S', time.localtime())}]:存在应答失败的签到，即将重试...")
                        else:
                            print(f"\n[{time.strftime('%H:%M:%S', time.localtime())}]:所有正进行的签到应答成功，监测将继续进行...")
                            temp_data = {'rollcalls': []}
            except Exception as e:
                print(f"[{time.strftime("%H:%M:%S", time.localtime())}]:发生错误 -{e}")

        elif res['status'] != 200:
            print("失去连接，请重新登录。")
            break
        time.sleep(interval)

    driver.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("用户中断，程序退出。")
    except Exception as e:
        print(f"发生错误，程序退出。\n{e}")
