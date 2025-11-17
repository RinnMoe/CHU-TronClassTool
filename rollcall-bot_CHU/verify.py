import uuid
import requests
import time
import asyncio
import aiohttp
import cv2
import json
from urllib.parse import urlparse, parse_qs
from config import get_base_url
from parse_qr import parse_sign_qr_code
from getimage import getimage

HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36 Edg/141.0.0.0",
        "Content-Type": "application/json"
    }

def pad(i):
    return str(i).zfill(4)


# AIOHTTP version of send_code transplanted from XMU-Rollcall-Bot-CLI(v3)
async def send_code_async(driver, rollcall_id):
    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer_number_rollcall"
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}

    stop_flag = asyncio.Event()
    found_code = None

    async def put_request(session, i):
        nonlocal found_code
        if stop_flag.is_set():
            return None
        payload = {
            "deviceId": str(uuid.uuid4()),
            "numberCode": pad(i),
        }
        try:
            async with session.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    found_code = pad(i)
                    stop_flag.set()
                    return found_code
        except asyncio.CancelledError:
            raise
        except Exception:
            # ignore request errors and keep trying others
            return None
        return None

    print("正在遍历签到码...")
    t00 = time.time()

    # limit concurrent connections similar to ThreadPoolExecutor max_workers
    connector = aiohttp.TCPConnector(limit=200)
    async with aiohttp.ClientSession(headers=HEADERS, cookies=cookies, connector=connector) as session:
        tasks = [asyncio.create_task(put_request(session, i)) for i in range(10000)]
        pending = set(tasks)
        try:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for d in done:
                    try:
                        res = d.result()
                    except Exception:
                        res = None
                    if res:
                        # cancel the rest
                        for p in pending:
                            p.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        print("签到码:", res)
                        t01 = time.time()
                        print("用时: %.2f 秒" % (t01 - t00))
                        return True
            # none found
            t01 = time.time()
            print("失败。\n用时: %.2f 秒" % (t01 - t00))
            return False
        finally:
            # ensure cleanup
            if pending:
                for p in pending:
                    p.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

# qrcode decoder from https://github.com/wilinz/fuck_tronclass_sign/
def scan_url_analysis(e: str):
    # 如果 URL 包含 "/j?p=" 且不是以 "http" 开头，拼接基础 URL
    if "/j?p=" in e and not e.startswith("http"):
        e = base_url + e
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



def send_code(driver, rollcall_id):
    return asyncio.run(send_code_async(driver, rollcall_id))


def send_radar(driver, rollcall_id, latitude, longitude):
    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer?api_version=1.76"
    payload = {
        "accuracy": 35,
        "altitude": 0,
        "altitudeAccuracy": None,
        "deviceId": str(uuid.uuid1()),
        "heading": None,
        "latitude": latitude,
        "longitude": longitude,  # 从config文件获取
        "speed": None
    }
    res = requests.put(url, json=payload, headers=HEADERS, cookies={c['name']: c['value'] for c in driver.get_cookies()})
    if res.status_code == 200:
        return True
    return False


def send_qr(driver, rollcall_id, course_id):
    #getimage by livestream based on course_id
    image = None  #PLACEHOLDER
    image = getimage(course_id)


    detector = cv2.QRCodeDetector()
    qr_text, bbox, _ = detector.detectAndDecode(image)

    qr_data = {"courseId": 0, "data": "0", "rollcallId": 0}
    if qr_text:
        qr_data = scan_url_analysis(qr_text)
    else:
        print('未能识别二维码内容')


    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer_qr_rollcall"
    payload = {
        "data": qr_data['data'],
        "deviceId": str(uuid.uuid4()),
    }
    res = requests.put(url, json=payload, headers=HEADERS, cookies={c['name']: c['value'] for c in driver.get_cookies()})
    if res.status_code == 200:
        return True
    return False