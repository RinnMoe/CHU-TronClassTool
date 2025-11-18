import json
from rich import print

def reset_config(config_path: str = "config.json") -> dict:
    """
    交互式创建或重置配置文件，并返回配置字典。
    """
    print("\n初次运行或配置损坏，正在重置配置 config.json，请填写相关信息。")
    username = input("请输入您的学号: (可留空)") or ""
    password = input("请输入您的密码: (可留空)") or ""
    base_url = input(
        "请输入 TronClass 平台地址 (默认 https://course-online.chd.edu.cn): "
    ) or "https://course-online.chd.edu.cn"
    cas_url = input(
        "请输入统一身份认证地址 (默认 https://ids.chd.edu.cn): "
    ) or "https://ids.chd.edu.cn"
    interval = input("请输入轮询间隔，单位秒 (默认 5): ") or 5
    longitude = input("请输入签到经度 (默认 113.000000): ") or 113.0
    latitude = input("请输入签到纬度 (默认 28.000000): ") or 28.0
    driver_path = input("请输入 ChromeDriver 路径 (默认 chromedriver.exe): ") or "chromedriver.exe"

    config = {
        "username": username,
        "password": password,
        "base_url": base_url,
        "cas_url": cas_url,
        "interval": int(interval),
        "longitude": float(longitude),
        "latitude": float(latitude),
        "driver": driver_path,
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

    return config


def load_config(config_path: str = "config.json") -> dict:
    """
    加载配置文件；如果不存在/损坏/缺少关键字段，则调用 reset_config 重建。
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        required_keys = [
            "base_url",
            "interval",
            "longitude",
            "latitude",
            "driver",
        ]
        for k in required_keys:
            if k not in config:
                raise KeyError(k)

        return config

    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return reset_config(config_path)


def get_base_url() -> str:
    """
    便捷函数，返回配置中的 base_url。
    """
    cfg = load_config()
    return cfg["base_url"]