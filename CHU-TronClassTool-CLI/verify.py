import uuid
import requests
import time
import asyncio
import aiohttp
import json
from urllib.parse import urlparse, parse_qs
from config import get_base_url
from parse_qr import parse_sign_qr_code
from qr_utils import get_qr_text
from position import get_position


def get_headers(driver):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36 TronClass/Common",
        "Content-Type": "application/json",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'sec-ch-ua-platform': "\"Android\"",
        'x-requested-with': "XMLHttpRequest",
        'x-session-id': f"{driver.get_session_id()}",
        }
    return headers

def pad(i):
    return str(i).zfill(4)

# qrcode decoder from https://github.com/wilinz/fuck_tronclass_sign/
def scan_url_analysis(e: str):
    # 如果 URL 包含 "/j?p=" 且不是以 "http" 开头，拼接基础 URL
    if "/j?p=" in e and not e.startswith("http"):
        e = get_base_url() + e
    # 如果仍然不是 HTTP 链接，直接返回
    if not e.startswith("http"):
        return e
    try:
        n = urlparse(e)
        # print(n)
    except Exception:
        return e
    # 处理特定路径
    if n.path in ["/j", "/scanner-jumper"]:
        o = parse_qs(n.query)
        # print(o)
        r = None
        try:
            a = o.get("_p", [None])[0]
            # print(a)
            if a:
                r = json.loads(a)
        except Exception:
            pass
        if not r:
            p_value = o.get("p", [""])[0]
            # print(p_value)
            r = parse_sign_qr_code(p_value)
            # print(r)
        return json.dumps(r) if r and isinstance(r, dict) and r else e
    return e


def send_code(driver, rollcall_id, cookies):
    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer_number_rollcall"
    headers = get_headers(driver)
    print("正在遍历签到码...")
    t00 = time.time()

    async def put_request(i, session, stop_flag, url, sem, timeout):
        if stop_flag.is_set():
            return None
        async with sem:
            if stop_flag.is_set():
                return None
            payload = {
                "deviceId": str(uuid.uuid4()),
                "numberCode": pad(i)
            }
            try:
                async with session.put(url, json=payload, timeout=timeout) as r:
                    if r.status == 200:
                        stop_flag.set()
                        return pad(i)
            except Exception:
                pass
            return None

    async def main():
        stop_flag = asyncio.Event()
        sem = asyncio.Semaphore(200)
        timeout = aiohttp.ClientTimeout(total=5)
        # 直接传 cookies，避免 CookieJar 行为差异
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            # 创建 Task 而不是原始协程
            tasks = [asyncio.create_task(put_request(i, session, stop_flag, url, sem, timeout)) for i in range(10000)]
            try:
                for coro in asyncio.as_completed(tasks):
                    res = await coro
                    if res is not None:
                        # 取消其余未完成的 Task
                        for t in tasks:
                            if not t.done():
                                t.cancel()
                        print("成功获取到签到码:", res)
                        t01 = time.time()
                        print("用时: %.2f 秒" % (t01 - t00))
                        return True
            finally:
                # 确保所有 task 结束
                for t in tasks:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        t01 = time.time()
        print("失败。\n用时: %.2f 秒" % (t01 - t00))
        return False

    return asyncio.run(main())

def send_radar(driver, rollcall_id, course_id, cookies):
    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer?api_version=1.76"
    headers = get_headers(driver)
    longitude, latitude = get_position(driver, course_id)
    payload = {
        "deviceId": str(uuid.uuid1()),
        "latitude": latitude,
        "longitude": longitude,
        "speed": None,
        "accuracy": 30,
        "altitude": None,
        "altitudeAccuracy": None,
        "heading": None
    }
    res = requests.put(url, json=payload, headers=headers, cookies=cookies)
    if res.status_code == 200:
        return True
    return False


def send_qr(driver, rollcall_id, course_id, cookies):
    print('尝试通过直播流获取二维码内容...')
    qr_text = get_qr_text(driver, course_id)
    qr_data = {"courseId": 0, "data": "0", "rollcallId": 0}
    if qr_text:
        qr_data = scan_url_analysis(qr_text)
        print(f'解析成功，二维码内容：{qr_data}')
    else:
        print('未能识别二维码内容')

    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer_qr_rollcall"
    headers = get_headers(driver)
    payload = {
        "data": qr_data['data'],
        "deviceId": str(uuid.uuid4()),
    }
    res = requests.put(url, json=payload, headers=headers, cookies=cookies)
    if res.status_code == 200:
        return True
    return False