import time
from verify import send_code, send_radar

def decode_rollcall(data):
    rollcalls = data['rollcalls']
    result = []
    if rollcalls:
        rollcall_count = len(rollcalls)
        for rollcall in rollcalls:
            result.append(
                {
                    'course_title': rollcall['course_title'],
                    'created_by_name': rollcall['created_by_name'],
                    'department_name': rollcall['department_name'],
                    'is_expired': rollcall['is_expired'],
                    'is_number': rollcall['is_number'],
                    'is_radar': rollcall['is_radar'],
                    'rollcall_id': rollcall['rollcall_id'],
                    'rollcall_status': rollcall['rollcall_status'],
                    'scored': rollcall['scored'],
                    'status': rollcall['status']
                }
            )
    else:
        rollcall_count = 0
    return rollcall_count, result

def parse_rollcalls(data, driver, longitude, latitude):
    undone = 0
    count, rollcalls = decode_rollcall(data)
    if count:
        print(time.strftime("%H:%M:%S", time.localtime()),f"监测到新的签到活动。\n")
        for i in range(count):
            print(f"第 {i+1} 个，共 {count} 个：")
            print(f"课程名称：{rollcalls[i]['course_title']}")
            print(f"签到创建：{rollcalls[i]['created_by_name']}")
            print(f"签到状态：{rollcalls[i]['rollcall_status']}")
            print(f"是否计分：{rollcalls[i]['scored']}")
            print(f"出勤情况：{rollcalls[i]['status']}")
            if not rollcalls[i]['status'] == 'absent':
                undone = 0
            if rollcalls[i]['source'] == "number":
                temp_str = "数字签到"
            elif rollcalls[i]['source'] == "qr":
                temp_str = "扫码签到"
            elif rollcalls[i]['source'] == "radar":
                temp_str = "雷达签到"
            elif rollcalls[i]['source'] == "merged":
                if not rollcalls[i]['children']['status'] == 'absent':
                    undone = 0
                if rollcalls[i]['children']['source'] == "number":
                    temp_str = "数字签到"
                elif rollcalls[i]['children']['source'] == "qr":
                    temp_str = "扫码签到"
                elif rollcalls[i]['children']['source'] == "radar":
                    temp_str = "雷达签到"
            else:
                temp_str = "未识别"
                print(f'未能识别该签到类型-{rollcalls[i]['source']}')
            print(f"签到类型：{temp_str}\n")
            if undone:
                if temp_str == "数字签到":
                    if send_code(driver, rollcalls[i]['rollcall_id']):
                        print("数字签到成功！")
                        return True
                    else:
                        print("数字签到失败。")
                        return False
                elif temp_str == "扫码签到":
                    print("暂不支持扫码签到")
                    return False
                elif temp_str == "雷达签到":
                    if send_radar(driver, rollcalls[i]['rollcall_id'], longitude, latitude):
                        print("雷达签到成功！")
                        return True
                    else:
                        print("雷达签到失败。")
                        return False
                elif temp_str == "未识别":
                    print("未知类型的签到失败。")
                    return False
            else:
                print("该签到已完成。")
                return True
    else:
        print("当前无签到活动。")
        return False
