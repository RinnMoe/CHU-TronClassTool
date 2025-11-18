# CHU-TronClassTool by Rinn
# based on https://github.com/KrsMt-0113/XMU-Rollcall-Bot
ver = "0.3.3"

import datetime
import time
import json
import requests
from rich import print
from parse_rollcalls import parse_rollcalls
from cas_login import login as cas_login
from login import login as browser_login
from config import load_config

def main():
    print(f"CHU-TronClassTool {ver} transplanted by Rinn")
    print("=================")
    print('正在初始化...', end='')

    config = load_config()
    username = config.get("username", '') or ''
    password = config.get("password", '') or ''
    base_url = config["base_url"]
    cas_url = config["cas_url"]
    interval = config["interval"]
    driver_path = config["driver"]

    print('完成')
    print(f"当前配置: \n平台地址: {base_url} \n轮询间隔: {interval}秒")
    print("=================")


    try:
        driver = cas_login(username, password,cas_url, interval)
    except Exception as e:
        print(f'{e}\n尝试使用浏览器登录...')
        try:
            driver = browser_login(username, password, driver_path, interval)
        except Exception as e:
            print(f'浏览器登录失败 - {e}\n程序退出。')
            time.sleep(2)
            return None

    base_url = config["base_url"]
    interval = config["interval"]
    longitude = config["longitude"]
    latitude = config["latitude"]

    # 签到列表获取接口，轮询间隔，轮询脚本
    api_url = f"{base_url}/api/radar/rollcalls"
    fetch_script = """
    const url = arguments[0];
    const callback = arguments[arguments.length - 1];
    fetch(url, {credentials: 'include'})
      .then(resp => resp.text().then(text => callback({status: resp.status, ok: resp.ok, text: text})))
      .catch(err => callback({error: String(err)}));
    """

    print(f"获取信息中...", end='')
    user_name = requests.get(f"{base_url}/api/profile", cookies={c["name"]: c["value"] for c in driver.get_cookies()}).json()['name']
    print(f"用户 {user_name} 登录成功")
    res = requests.get(api_url, cookies={c["name"]: c["value"] for c in driver.get_cookies()})
    if res.status_code == 200:
        print("启动监测...")
    else:
        print("登录失败。3秒后程序退出。")
        time.sleep(3)
        exit(0)

    time.sleep(0.5)

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
                        if not parse_rollcalls(temp_data, driver, longitude, latitude):
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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        time.sleep(2)
        print("用户中断，程序退出。")
    except Exception as e:
        time.sleep(2)
        print(f"发生错误，程序退出。\n{e}")
