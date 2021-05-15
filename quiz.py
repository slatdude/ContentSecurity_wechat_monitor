"""
随机生成验证码，图片（base64Str）
基于pillow
"""

import random
import string
from PIL import Image, ImageFont, ImageDraw
import base64
from io import BytesIO

__version__ = 'v1'


def _randColor():
    """随机颜色"""
    return random.randint(32, 127), random.randint(32, 127), random.randint(32, 127)


def _getText():
    """4位验证码"""
    return ''.join(random.sample(string.ascii_letters + string.digits, 4))


def _drawLines(draw, num, width, height):
    """划线"""
    for temp in range(num):
        x1 = random.randint(0, width / 2)
        y1 = random.randint(0, height / 2)
        x2 = random.randint(0, width)
        y2 = random.randint(height / 2, height)
        draw.line(((x1, y1), (x2, y2)), fill='black', width=1)


def getVerifyCode():
    """
    获取图片对象, 验证码字符串
    img.save(‘vc.jpg’) 保存验证码图片
    :return: (img对象, str)
    """
    code = _getText()
    # 图片大小
    width, height = 100, 36
    # 新图片对象
    image = Image.new('RGB', (width, height), 'white')
    # 字体
    font = ImageFont.truetype('./fonts/Bosk.ttf', 30)
    # draw对象
    draw = ImageDraw.Draw(image)
    # 绘制字符串
    for item in range(4):
        draw.text((8 + 24 * item, random.randint(-3, 3)),
                  text=code[item], fill=_randColor(), font=font)
    # 划线
    _drawLines(draw, 2, width, height)
    image.save('./temp_verify.jpg')
    return image, code


def getBase64Code():
    """
    获取验证码base64数据, 验证码字符串
    :return: (base64Str, str)
    """
    image, code = getVerifyCode()
    outputBuffer = BytesIO()
    image.save(outputBuffer, format='JPEG')
    byteData = outputBuffer.getvalue()
    base64Str = base64.b64encode(byteData)
    return base64Str.decode("utf-8"), code

# img, code = getVerifyCode()
# img.save("save.jpg")
# print(code)