import requests
import json
from config import get_base_url


def load_locations():
    with open('position.json', encoding="utf-8") as f:
        config = json.load(f)
    return {item["name"]: item for item in config}


def extract_prefix(classroom_name):
    if isinstance(classroom_name, str) and len(classroom_name) >= 3:
        return classroom_name[1:3]
    return None


def get_position(driver, course_id):
    print('尝试获取课程地点...')
    base_url = get_base_url()
    defult_lon, default_lat = 34.3701, 108.8982
    try:
        locations = load_locations()
    except Exception:
        print("获取课程地点失败, 使用默认位置 E1")
        return defult_lon, default_lat

    # 请求进行中的直播活动
    live_list_url = f"{base_url}/api/courses/{course_id}/live-activities?status=in_progress"
    list_res = requests.get(live_list_url, cookies={c['name']: c['value'] for c in driver.get_cookies()})

    if list_res.status_code != 200:
        print("获取课程地点失败, 使用默认位置 E2")
        return defult_lon, default_lat

    items = list_res.json().get("items", [])
    if not items:
        print("获取课程地点失败, 使用默认位置 E3")
        return defult_lon, default_lat

    # 请求直播详情
    live_info_url = f"{base_url}/api/activities/{items[0]['id']}"
    info_res = requests.get(live_info_url, cookies={c['name']: c['value'] for c in driver.get_cookies()})

    if info_res.status_code != 200:
        print("获取课程地点失败, 使用默认位置 E4")
        return defult_lon, default_lat

    live_info = info_res.json()
    classroom_name = live_info['data']['external_live_detail']['room']['room_name']

    prefix = extract_prefix(classroom_name)

    if prefix in locations:
        lon = locations[prefix]['lon']
        lat = locations[prefix]['lat']
        print(f"获取课程地点成功：{prefix}, 经度: {lon}, 纬度: {lat}")
        return lon, lat
    else:
        print("获取课程地点失败, 使用默认位置 E5")
        return defult_lon, default_lat
