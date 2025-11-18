import re
import time
import numpy as np
import requests
import subprocess
import cv2
from config import get_base_url


def identify(text):
    payload_pattern = re.compile(r"/j\?p=0~.3t80!3~([0-9a-fA-F]{42})!4~.95bc")
    return payload_pattern.findall(text)


def get_livestream(driver, course_id):
    base_url = get_base_url()
    live_list_url = f"{base_url}/api/courses/{course_id}/live-activities?status=in_progress"
    list_res = requests.get(live_list_url, cookies={c['name']: c['value'] for c in driver.get_cookies()}) #获取进行中的直播活动列表
    if list_res.status_code == 200:
        data = list_res.json()
        items = data.get("items", [])
        if items:
            live_info_url = f"{base_url}/api/activities/{items[0]['id']}"
            info_res = requests.get(live_info_url, cookies={c['name']: c['value'] for c in driver.get_cookies()}) #获取直播活动flv流
            if info_res.status_code == 200:
                live_info = info_res.json()
                streams = live_info['data']['streams']
                encoder_stream = []
                for item in streams:
                    if item.get("label") == "encoder":
                        encoder_stream.append(item.get("flv_src"))
                return encoder_stream[0] #畅课不知道为什么会同时有多个flv流，只取第一个
            else:
                print("获取直播流信息失败")
    else:
        print("获取直播活动列表失败")
    return None

def get_qr_text(driver, course_id, timeout_sec=60):
    # 从课程直播流中获取包含二维码的截图，如有多个码则进行筛选。
    flv_url = get_livestream(driver, course_id)
    if not flv_url:
        print("未找到正在进行的直播活动")
        return None

    # 获取视频分辨率
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=s=x:p=0", flv_url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    try:
        w, h = map(int, probe.stdout.strip().split("x"))
    except:
        print("直播分辨率获取失败")
        return None

    # ffmpeg 解码
    p = subprocess.Popen(
        ["ffmpeg", "-i", flv_url, "-loglevel", "quiet",
         "-an", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    start = time.time()
    detector = cv2.barcode_BarcodeDetector()

    try:
        while True:
            if time.time() - start > timeout_sec:
                print("在视频中查找签到码超时")
                return None

            raw = p.stdout.read(w * h * 3)
            if len(raw) < w * h * 3:
                continue

            frame = np.frombuffer(raw, np.uint8).reshape((h, w, 3))
            ok, decoded_info, points, _ = detector.detectAndDecode(frame)

            if not ok or not decoded_info:
                continue

            # 遍历所有二维码
            for qr_text in decoded_info:
                if not qr_text:
                    continue

                if identify(qr_text):
                    print("成功在视频中查找到签到码")
                    return qr_text

    finally:
        p.kill()