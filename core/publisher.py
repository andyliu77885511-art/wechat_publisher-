from typing import Union
"""
publisher.py — 微信公众号发布模块
功能：获取 access_token、上传封面图、创建草稿、发布草稿
"""
import time
import logging
import requests
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# access_token 内存缓存（token 本体 + 过期时间戳）
_token_cache: dict = {"token": "", "expires_at": 0}

# 微信接口超时
_TIMEOUT = 15


class WechatAPIError(Exception):
    """微信 API 返回错误码时抛出"""
    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"微信 API 错误 [{errcode}]: {errmsg}")


def _check_wx_resp(data: dict) -> dict:
    """检查微信 API 响应体，有 errcode 且非 0 则抛出异常"""
    errcode = data.get("errcode", 0)
    if errcode != 0:
        raise WechatAPIError(errcode, data.get("errmsg", "unknown"))
    return data


# ── Access Token ───────────────────────────────────────────────────────────────

def get_access_token() -> str:
    """
    获取并缓存微信 access_token。
    token 有效期 7200s，提前 300s 刷新。
    """
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    if not config.WX_APP_ID or not config.WX_APP_SECRET:
        raise EnvironmentError("未配置 WX_APP_ID 或 WX_APP_SECRET，请检查 .env 文件")

    logger.info("[publisher] 正在获取微信 access_token ...")
    resp = requests.get(
        config.WX_TOKEN_URL,
        params={
            "grant_type": "client_credential",
            "appid": config.WX_APP_ID,
            "secret": config.WX_APP_SECRET,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    _check_wx_resp(data)

    token = data["access_token"]
    expires_in = data.get("expires_in", 7200)

    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in - 300  # 提前 5 分钟过期

    logger.info("[publisher] access_token 获取成功")
    return token


def _invalidate_token():
    """在收到 40001/42001 时主动清除缓存，下次重新获取"""
    _token_cache["token"] = ""
    _token_cache["expires_at"] = 0


# ── 封面图上传 ──────────────────────────────────────────────────────────────────

def upload_image(image_path: Union[str, Path]) -> str:
    """
    上传封面图到微信素材库（永久素材）。

    Args:
        image_path: 本地图片路径，支持 jpg/png

    Returns:
        media_id — 上传后的素材 ID
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"封面图文件不存在：{image_path}")

    suffix = image_path.suffix.lower().lstrip(".")
    if suffix not in ("jpg", "jpeg", "png"):
        raise ValueError(f"不支持的图片格式：{suffix}，请使用 jpg 或 png")

    token = get_access_token()
    upload_url = "https://api.weixin.qq.com/cgi-bin/material/add_material"

    logger.info(f"[publisher] 上传封面图：{image_path.name}")
    with open(image_path, "rb") as f:
        resp = requests.post(
            upload_url,
            params={"access_token": token, "type": "image"},
            files={"media": (image_path.name, f, f"image/{suffix}")},
            timeout=_TIMEOUT,
        )
    resp.raise_for_status()
    data = resp.json()

    # token 过期时重试一次
    if data.get("errcode") in (40001, 42001):
        _invalidate_token()
        token = get_access_token()
        with open(image_path, "rb") as f:
            resp = requests.post(
                upload_url,
                params={"access_token": token, "type": "image"},
                files={"media": (image_path.name, f, f"image/{suffix}")},
                timeout=_TIMEOUT,
            )
        resp.raise_for_status()
        data = resp.json()

    _check_wx_resp(data)
    media_id = data["media_id"]
    logger.info(f"[publisher] 封面图上传成功，media_id：{media_id}")
    return media_id


# ── 创建草稿 ────────────────────────────────────────────────────────────────────

def create_draft(title: str, content: str, cover_media_id: str = "") -> str:
    """
    创建图文草稿（draft/add 接口）。

    Args:
        title: 文章标题
        content: 文章 HTML 正文（微信需要 HTML 格式）
        cover_media_id: 封面图素材 ID，可为空（微信允许无封面）

    Returns:
        media_id — 草稿 media_id，供发布使用
    """
    if not title:
        raise ValueError("文章标题不能为空")
    if not content:
        raise ValueError("文章正文不能为空")

    # 将纯文本换行符转为 HTML 段落（若 content 已是 HTML 则跳过）
    if "<p>" not in content and "<br" not in content:
        html_content = "".join(
            f"<p>{line}</p>" if line.strip() else "<p><br/></p>"
            for line in content.splitlines()
        )
    else:
        html_content = content

    token = get_access_token()
    article = {
        "title": title,
        "author": "",
        "digest": "",
        "content": html_content,
        "content_source_url": "",
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    if cover_media_id:
        article["thumb_media_id"] = cover_media_id

    payload = {"articles": [article]}

    logger.info(f"[publisher] 创建草稿：{title}")
    resp = requests.post(
        config.WX_ADD_NEWS_URL,
        params={"access_token": token},
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("errcode") in (40001, 42001):
        _invalidate_token()
        token = get_access_token()
        resp = requests.post(
            config.WX_ADD_NEWS_URL,
            params={"access_token": token},
            json=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

    _check_wx_resp(data)
    media_id = data["media_id"]
    logger.info(f"[publisher] 草稿创建成功，media_id：{media_id}")
    return media_id


# ── 发布草稿 ────────────────────────────────────────────────────────────────────

def publish_draft(media_id: str) -> str:
    """
    将草稿提交群发发布（freepublish/submit 接口）。

    Args:
        media_id: create_draft 返回的草稿 media_id

    Returns:
        publish_id — 发布任务 ID
    """
    if not media_id:
        raise ValueError("media_id 不能为空")

    token = get_access_token()
    payload = {"media_id": media_id}

    logger.info(f"[publisher] 提交发布，media_id：{media_id}")
    resp = requests.post(
        config.WX_FREE_PUBLISH_URL,
        params={"access_token": token},
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("errcode") in (40001, 42001):
        _invalidate_token()
        token = get_access_token()
        resp = requests.post(
            config.WX_FREE_PUBLISH_URL,
            params={"access_token": token},
            json=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

    _check_wx_resp(data)
    publish_id = data.get("publish_id", "")
    logger.info(f"[publisher] 发布任务已提交，publish_id：{publish_id}")
    return publish_id
