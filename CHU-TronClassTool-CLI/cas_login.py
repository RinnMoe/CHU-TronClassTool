import json
import os
import time
import base64
import requests
from typing import Tuple
from rich import print
from bs4 import BeautifulSoup
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


class SessionDriver:
    """
    使用 requests.Session 适配老driver调用。
    """

    def __init__(self, session: requests.Session):
        self.session = session

    def get_cookies(self):
        return [{"name": c.name, "value": c.value} for c in self.session.cookies]

    def execute_async_script(self, script, url, timeout=15):
        try:
            resp = self.session.get(url, timeout=timeout)
            return {"status": resp.status_code, "ok": resp.ok, "text": resp.text}
        except Exception as e:
            return {"error": str(e)}


COOKIE_FILE = "cookies.json"

def save_cookies_file(cookies):
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
    except:
        pass


def load_cookie_file():
    if not os.path.exists(COOKIE_FILE):
        return None
    try:
        with open(COOKIE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def load_session(cookies_list):
    s = requests.Session()
    for c in cookies_list:
        s.cookies.set(
            c.get("name"),
            c.get("value"),
            domain=c.get("domain", None),
            path=c.get("path", "/")
        )
    return s


def random_string(n: int) -> str:
    aes_chars = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"

    return "".join(random.choice(aes_chars) for _ in range(n))


def encrypt_password(password: str, salt: str) -> str:
    raw = (random_string(64) + password).encode("utf-8")
    key = salt.encode("utf-8")
    iv = random_string(16).encode("utf-8")

    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(raw, AES.block_size))
    return base64.b64encode(encrypted).decode()


def cas_login(username: str, password: str, cas_url: str):
    """
    返回一个已登录的 requests.Session()
    """
    session = requests.Session()

    resp = session.get(cas_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    lt = soup.find("input", {"name": "lt"})["value"]
    execution = soup.find("input", {"name": "execution"})["value"]
    salt = soup.find("input", {"id": "pwdEncryptSalt"})["value"]

    encrypted_pwd = encrypt_password(password, salt)

    data = {
        "username": username,
        "password": encrypted_pwd,
        "lt": lt,
        "execution": execution,
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin"
    }

    resp = session.post(cas_url, data=data, allow_redirects=True)

    if ("统一身份认证" in resp.text) or ("密码错误" in resp.text) or ("登录失败" in resp.text):
        raise RuntimeError("CAS 登录失败，请检查账号密码是否正确")

    return session

def login(username, password) -> Tuple[SessionDriver, dict]:
    # 尝试 cookie 恢复
    old_cookies = load_cookie_file()
    if old_cookies:
        print("尝试恢复登录态...", end="")
        s = load_session(old_cookies)
        try:
            r = s.get(f'{api_url}/user/index#/', timeout=10)
            if r.ok and ("统一身份认证平台" not in r.text):
                print("[green]成功[/]")
                return SessionDriver(s), config
            else:
                print("[yellow]失效，重新登录[/]")
        except:
            print("[yellow]失效，重新登录[/]")

    print("[cyan]使用统一身份认证登录...[/]", end="")

    if not username or not password:
        raise RuntimeError("配置文件缺少 username / password 无法使用此方法登录")

    # 登录
    s = cas_login(username, password, cas_url)

    # 保存 cookies
    cookies = [{"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
               for c in s.cookies]
    save_cookies_file(cookies)

    print(f"[green]成功[/]")
    time.sleep(interval)

    return SessionDriver(s), config
