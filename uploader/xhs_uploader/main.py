import configparser
import json
import pathlib
from time import sleep

import requests
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

from conf import BASE_DIR, XHS_SERVER, XHS_SERVER_A1, LOCAL_CHROME_PATH
from xhs import XhsClient
from utils.log import xhs_logger
import os
import datetime

config = configparser.RawConfigParser()
config.read('accounts.ini')


def sign_local(uri, data=None, a1="", web_session=""):
    for _ in range(10):
        try:
            with sync_playwright() as playwright:
                stealth_js_path = pathlib.Path(BASE_DIR / "utils/stealth.min.js")
                chromium = playwright.chromium

                # 如果一直失败可尝试设置成 False 让其打开浏览器，适当添加 sleep 可查看浏览器状态
                browser = chromium.launch(headless=True)

                browser_context = browser.new_context()
                browser_context.add_init_script(path=stealth_js_path)
                context_page = browser_context.new_page()
                context_page.goto("https://www.xiaohongshu.com")
                browser_context.add_cookies([
                    {'name': 'a1', 'value': a1, 'domain': ".xiaohongshu.com", 'path': "/"}]
                )
                context_page.reload()
                # 这个地方设置完浏览器 cookie 之后，如果这儿不 sleep 一下签名获取就失败了，如果经常失败请设置长一点试试
                sleep(2)
                encrypt_params = context_page.evaluate("([url, data]) => window._webmsxyw(url, data)", [uri, data])
                return {
                    "x-s": encrypt_params["X-s"],
                    "x-t": str(encrypt_params["X-t"])
                }
        except Exception:
            # 这儿有时会出现 window._webmsxyw is not a function 或未知跳转错误，因此加一个失败重试趴
            pass
    raise Exception("重试了这么多次还是无法签名成功，寄寄寄")


def sign(uri, data=None, a1="", web_session=""):
    # 填写自己的 flask 签名服务端口地址
    res = requests.post(f"{XHS_SERVER}/sign",
                        json={"uri": uri, "data": data, "a1": a1, "web_session": web_session})
    signs = res.json()
    return {
        "x-s": signs["x-s"],
        "x-t": signs["x-t"]
    }


def beauty_print(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def get_xhs_client(account_file):
    with open(account_file) as f:
        data = json.load(f)
    cookies = ';'.join([item['name'] + '=' + (item['value'] if item['name']!='a1' else XHS_SERVER_A1) for item in data])
    print(cookies)
    # xhs_client = XhsClient(cookies, sign=lambda url,data,a1,web_session: sign(url,data,XHS_SERVER_A1,web_session), timeout=60)
    xhs_client = XhsClient(cookies, sign=sign, timeout=60)
    return xhs_client

async def cookie_auth(account_file):
    xhs_client = get_xhs_client(account_file)
    try:
        xhs_client.get_video_first_frame_image_id("3214")
        print("[+] cookie 有效")
        return True
    except:
        print("[+] cookie 失效")
        return False

async def xhs_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        xhs_logger.info('[+] cookie文件不存在或已失效，请更新小红书账号cookies')
    return True

class XHSVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, thumbnail_path=None, location=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.thumbnail_path = thumbnail_path
        self.location = location

    async def upload(self) -> None:
        # 加入到标题 补充标题（xhs 可以填1000字不写白不写）
        tags_str = ' '.join(['#' + tag for tag in self.tags])
        hash_tags_str = ''
        hash_tags = []
        topics = []
        # 获取hashtag
        xhs_client = get_xhs_client(self.account_file)
        for i in self.tags[:3]:
            topic_official = xhs_client.get_suggest_topic(i)
            if topic_official:
                topic_official[0]['type'] = 'topic'
                topic_one = topic_official[0]
                hash_tag_name = topic_one['name']
                hash_tags.append(hash_tag_name)
                topics.append(topic_one)

        hash_tags_str = ' ' + ' '.join(['#' + tag + '[话题]#' for tag in hash_tags])
        post_time = None if self.publish_date==0 else self.publish_date.strftime("%Y-%m-%d %H:%M:%S")
        cover_path = None if not self.thumbnail_path else self.thumbnail_path

        note = xhs_client.create_video_note(title=self.title[:20],
                                            video_path=self.file_path,
                                            desc=self.title + tags_str + hash_tags_str,
                                            topics=topics,
                                            is_private=False,
                                            post_time=post_time,
                                            cover_path=cover_path)

    async def main(self):
        await self.upload()
