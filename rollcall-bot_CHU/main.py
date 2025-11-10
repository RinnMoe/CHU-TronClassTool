# CHU-TronClassTool 0.1
# transplant by Rinn
# origin repository https://github.com/KrsMt-0113/XMU-Rollcall-Bot


import time
import json
import uuid
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.ie.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from parse_rollcalls import parse_rollcalls

# 读取学号、密码
with open("config.json", encoding='utf-8') as f:
    config = json.load(f)
    username = config["username"]
    password = config["password"]

# 签到列表获取接口，轮询间隔，轮询脚本
api_url = "https://course-online.chd.edu.cn/api/radar/rollcalls"
interval = 1.5 #全局休眠时间
fetch_script = """
const url = arguments[0];
const callback = arguments[arguments.length - 1];
fetch(url, {credentials: 'include'})
  .then(resp => resp.text().then(text => callback({status: resp.status, ok: resp.ok, text: text})))
  .catch(err => callback({error: String(err)}));
"""

chrome_options = Options()
# chrome_options.add_argument("--start-maximized")   # 有头调试
chrome_options.add_argument("--headless")  # 无头运行

# 启动selenium
print("CHU-TronClassTool 0.1\ntransplant by Rinn\n正在初始化...")
driver = webdriver.Chrome(chrome_options, service=Service('../chromedriver.exe'))

driver.get("https://course-online.chd.edu.cn/user/index#/")
print("已连接。开始登录。")

WebDriverWait(driver, 10, 0.5).until(EC.title_contains('统一身份认证平台'))
driver.find_element(By.ID, "username").send_keys(username)
driver.find_element(By.ID, "password").send_keys(password)
driver.find_element(By.ID, "login_submit").click()

WebDriverWait(driver, 100, 0.5).until(EC.title_contains('首页 - 畅课'))
print(f'用户{driver.find_element(By.ID, "userCurrentName").text}已登录成功')

res = requests.get(api_url, cookies={c['name']: c['value'] for c in driver.get_cookies()})
if res.status_code == 200:
    print("五秒后进入监测...")
else:
    print("登录失败。五秒后程序退出。")
    driver.quit()
    time.sleep(5)
    exit(0)

time.sleep(5)

deviceID = uuid.uuid4()
print(f"签到监测启动。")
start = time.time()
temp_data = {'rollcalls': []}
while True:
    res = driver.execute_async_script(fetch_script, api_url)
    if res['status'] == 200:
        text = res.get('text', '')
        try:
            data = json.loads(text)
            if temp_data == data:
                # print("当前无签到活动。")
                continue
            else:
                temp_data = data
                if len(temp_data['rollcalls']) > 0:
                    if not parse_rollcalls(temp_data, driver):
                        temp_data = {'rollcalls': []}
        except Exception as e:
            print(time.strftime("%H:%M:%S", time.localtime()), ":发生错误")

    elif res['status'] != 200:
        print("失去连接，请重新登录。")
        break
    time.sleep(interval)

driver.quit()
