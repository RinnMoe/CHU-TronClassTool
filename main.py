import time
import json
import uuid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from parse_rollcalls import parse_rollcalls

with open("config.json") as f:
    config = json.load(f)
    username = config["username"]
    password = config["password"]
api_url = "https://lnt.xmu.edu.cn/api/radar/rollcalls"
interval = 2.0  # 轮询间隔

fetch_script = """
const url = arguments[0];
const callback = arguments[arguments.length - 1];
fetch(url, {credentials: 'include'})
  .then(resp => resp.text().then(text => callback({status: resp.status, ok: resp.ok, text: text})))
  .catch(err => callback({error: String(err)}));
"""  # 轮询脚本

chrome_options = Options()
# chrome_options.add_argument("--start-maximized")   # 有头调试
chrome_options.add_argument("--headless")  # 无头运行


print("正在初始化...")
driver = webdriver.Chrome(options=chrome_options)

driver.get("https://lnt.xmu.edu.cn")
print("已连接到厦大数字化教学平台。")

WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.ID, "userNameLogin_a"))
).click()
driver.find_element(By.ID, "username").send_keys(username)
driver.find_element(By.ID, "password").send_keys(password)
driver.find_element(By.ID, "login_submit").click()

print("正在登录...")
time.sleep(5)

res = driver.execute_async_script(fetch_script, api_url)
if res['status'] == 200:
    print("登录成功！五秒后进入监控...")
else:
    print("请检查账号密码是否正确，如检查无误请手动登录并完成验证码认证。")
    driver.quit()
time.sleep(5)


deviceID = uuid.uuid4()
print(f"签到监控启动。")
start = time.time()
temp_data = {'rollcalls': []}
while True:
    res = driver.execute_async_script(fetch_script, api_url)
    if res['status'] == 200:
        text = res.get('text', '')
        try:
            data = json.loads(text)
            if temp_data == data:
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
