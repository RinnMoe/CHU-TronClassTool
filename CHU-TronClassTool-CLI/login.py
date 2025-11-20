import json
import os
import time
import base64
import requests
# import ddddocr
from PIL import Image
from io import BytesIO
from rich import print
from bs4 import BeautifulSoup
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from config import get_base_url


class SessionDriver:
    """
    使用 requests.Session 适配老driver调用。
    """

    def __init__(self, session: requests.Session):
        self.session = session

    def get_cookies(self):
        return [{"name": c.name, "value": c.value} for c in self.session.cookies]

    def get_session_id(self):
        cookies = self.get_cookies()
        for c in cookies:
            if c["name"] == "session":
                return c["value"]
        return None

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


def captcha_check(username, cas_url, session):
    _time = int(time.time() * 1000)
    r = session.get(f"{cas_url}/checkNeedCaptcha.htl?username={username}&_={_time}").json()
    # print(r)
    if r.get("isNeed"):
        p = session.get(f"{cas_url}/getCaptcha.htl?{_time}")
        # img_bytes = p.content
        # ocr = ddddocr.DdddOcr()
        # code = ocr.classification(img_bytes)
        img = Image.open(BytesIO(p.content))
        img.show()
        # print(code)
        captcha = input('输入验证码: ')
        return captcha
    else:
        return None


def cas_login(username: str, password: str, cas_url: str):
    session = requests.Session()

    resp = session.get(cas_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    lt = soup.find("input", {"name": "lt"})["value"]
    execution = soup.find("input", {"name": "execution"})["value"]
    salt = soup.find("input", {"id": "pwdEncryptSalt"})["value"]

    encrypted_pwd = encrypt_password(password, salt)

    captcha = captcha_check(username, cas_url, session)

    data = {
        "username": username,
        "password": encrypted_pwd,
        "captcha": captcha or "",
        "lt": lt,
        "dllt": "generalLogin",
        "cllt": "userNameLogin",
        "execution": execution,
        "_eventId": "submit",
    }

    resp = session.post(f'{cas_url}/login', data=data, allow_redirects=True)

    if ("统一身份认证" in resp.text) or ("密码错误" in resp.text) or ("登录失败" in resp.text):
        raise RuntimeError("CAS 登录失败")

    return session


def login(username, password, cas_url, interval) -> SessionDriver:
    base_url = get_base_url()

    # 尝试 cookie 恢复
    old_cookies = load_cookie_file()
    if old_cookies:
        print("尝试恢复登录态...", end="")
        s = load_session(old_cookies)
        try:
            r = s.get(f'{base_url}/user/index#/', timeout=10)
            if r.ok and ("统一身份认证平台" not in r.text):
                print("[green]成功[/]")
                return SessionDriver(s)
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

    return SessionDriver(s)
