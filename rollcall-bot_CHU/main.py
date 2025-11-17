# CHU-TronClassTool by Rinn
# based on https://github.com/KrsMt-0113/XMU-Rollcall-Bot

ver = "0.3.1"

import datetime
import time
import json
import requests
from rich import print
from parse_rollcalls import parse_rollcalls
from login import login

def main():
    driver, config = login()

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

    res = requests.get(api_url, cookies={c["name"]: c["value"] for c in driver.get_cookies()})
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
