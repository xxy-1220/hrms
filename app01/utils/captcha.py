"""图片验证码生成工具（Pillow 实现）。

职责（对应任务书 T4 登录认证，涉及 T13 安全加固）：
  1. generate_captcha_code：生成随机字符“答案”；
  2. render_captcha_image：把答案画成 PNG 图片字节流（内存中完成，不写磁盘）。
拆成两步的原因：答案要存 Session 供后端比对，图片只发给浏览器，前端源码看不到
答案，必须人工识别。

术语：Pillow（PIL）= Python 图像处理库；BytesIO = 内存中的字节缓冲区，
相当于一个假文件，图片编码后直接从内存取走。
"""

# 讲解要点：
# 1. 页面现象：登录页验证码图里的字符是深色、大小不一、周围有细线和噪点 ——
#    就是下面“绘制字符 / 干扰线 / 噪点”三段循环画出来的，增加 OCR 识别难度。
# 2. 页面现象：验证码里从不出现 0、O、1、I —— CAPTCHA_CHARS 主动剔除了易混字符，
#    用户不会因为“到底是 0 还是 O”而登录失败。
# 3. 页面现象：点验证码图片能立刻换一张，项目目录也不会生成图片文件 ——
#    render_captcha_image 用 BytesIO 在内存里编码 PNG 后直接返回字节流。
# 4. 页面现象：登录时字母大小写都能通过 —— 这里生成只用大写字母，auth.py
#    校验时再 .upper() 统一。

import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CAPTCHA_CHARS = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def generate_captcha_code(length=4):
    return ''.join(random.choice(CAPTCHA_CHARS) for _ in range(length))


def render_captcha_image(code, width=130, height=44):
    image = Image.new('RGB', (width, height), (245, 247, 250))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=26)

    char_width = width // (len(code) + 1)
    for index, char in enumerate(code):
        x = char_width * (index + 1) - 8 + random.randint(-3, 3)
        y = random.randint(2, 10)
        color = (
            random.randint(20, 120),
            random.randint(20, 120),
            random.randint(20, 120),
        )
        draw.text((x, y), char, font=font, fill=color)

    for _ in range(6):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        draw.line(
            [start, end],
            fill=(
                random.randint(120, 220),
                random.randint(120, 220),
                random.randint(120, 220),
            ),
            width=1,
        )

    for _ in range(80):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=(
                random.randint(80, 200),
                random.randint(80, 200),
                random.randint(80, 200),
            ),
        )

    image = image.filter(ImageFilter.SMOOTH)

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()
