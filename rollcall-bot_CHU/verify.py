import uuid
import requests
import time
import asyncio
import aiohttp
from config import get_base_url

def pad(i):
    return str(i).zfill(4)


# AIOHTTP version of send_code transplanted from XMU-Rollcall-Bot-CLI(v3)
async def send_code_async(driver, rollcall_id):
    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer_number_rollcall"

    # prepare headers and cookies from selenium driver
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36 Edg/141.0.0.0",
        "Content-Type": "application/json",
    }
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
    async with aiohttp.ClientSession(headers=headers, cookies=cookies, connector=connector) as session:
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


# keep public API: provide sync wrapper
def send_code(driver, rollcall_id):
    return asyncio.run(send_code_async(driver, rollcall_id))



def send_radar(driver, rollcall_id, latitude, longitude):
    url = f"{get_base_url()}/api/rollcall/{rollcall_id}/answer?api_version=1.76"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36 Edg/141.0.0.0",
        "Content-Type": "application/json"
    }
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
    res = requests.put(url, json=payload, headers=headers, cookies={c['name']: c['value'] for c in driver.get_cookies()})
    if res.status_code == 200:
        return True
    return False