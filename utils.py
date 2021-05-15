import jieba
import sys
import json
import numpy as np
import base64
import os



# 数据库查
def find(collection, id):
    result = collection.find_one({"_id": id})
    if result:
        return result  # 返回一个字典，通过result["xxx"]的方式可以获取某个字段的值
    else:
        return False


# 数据库增
def insert(collection, id, inserted_dict, has_identifier=True):
    if find(collection, id) and has_identifier:
        return False
    else:
        # result = collection.insert_one(
        #     {"_id": id, "time_in": time.time(), "warning": 0, "time_last_warning": 0})
        result = collection.insert_one(inserted_dict)
        if find(collection, id):
            return True
        else:
            return False


# 数据库删
def delete(collection, id):
    if find(collection, id):
        collection.delete_one({"_id": id})
        if find(collection, id):
            return False
        else:
            return True
    else:
        return False


# 数据库改
def update(collection, id, field, value):
    result = collection.update_one({"_id": id}, {"$set": {field: value}})
    isok = find(collection, id)
    if isok[field] == value:
        return True
    else:
        return False


def warning_user(collection, contact):
    find_result = find(collection, contact.contact_id)
    warning_times = find_result["warning"]
    if warning_times > 2:
        return 0
    else:
        update(collection, contact.contact_id, "warning", warning_times + 1)
        return warning_times + 1



# ###########百度API#############

# 保证兼容python2以及python3
IS_PY3 = sys.version_info.major == 3
if IS_PY3:
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.error import URLError
    from urllib.parse import urlencode
    from urllib.parse import quote_plus

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

API_KEY = 'fpQ2Vg44Zntxxxxxxxxxxxxxxxx'

SECRET_KEY = 'OscxD3Nusrsssssssssssssssssss'


IMAGE_CENSOR = "https://aip.baidubce.com/rest/2.0/solution/v1/img_censor/v2/user_defined"

TEXT_CENSOR = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined";

"""  TOKEN start """
TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'


"""
    获取token
"""
def fetch_token():
    params = {'grant_type': 'client_credentials',
              'client_id': API_KEY,
              'client_secret': SECRET_KEY}
    post_data = urlencode(params)
    if (IS_PY3):
        post_data = post_data.encode('utf-8')
    req = Request(TOKEN_URL, post_data)
    try:
        f = urlopen(req, timeout=5)
        result_str = f.read()
    except URLError as err:
        print(err)
    if (IS_PY3):
        result_str = result_str.decode()


    result = json.loads(result_str)

    if ('access_token' in result.keys() and 'scope' in result.keys()):
        if not 'brain_all_scope' in result['scope'].split(' '):
            print ('please ensure has check the  ability')
            exit()
        return result['access_token']
    else:
        print ('please overwrite the correct API_KEY and SECRET_KEY')
        exit()

"""
    读取文件
"""
def read_file(image_path):
    f = None
    try:
        f = open(image_path, 'rb')
        return f.read()
    except:
        print('read image file fail')
        return None
    finally:
        if f:
            f.close()


"""
    调用远程服务
"""
def request(url, data):
    req = Request(url, data.encode('utf-8'))
    has_error = False
    try:
        f = urlopen(req)
        result_str = f.read()
        if (IS_PY3):
            result_str = result_str.decode()
        return result_str
    except  URLError as err:
        print(err)




# predefined information.
HELPER_CONTACT_NAME = 'ＫＩＥＲＡＮ．'

bot_contact_id = 'wxid_xxxxxxxxxxxxxx'

owner_contact_id_list = [
                         'wxid_xxxxxxxxxxxxxxx'
                         ]

bot_owner_room_id_list = ['xxxxxxxxxxx@chatroom'
                          ]

MONGO_HOST = "HOST"
MONGO_USER = "USER"
MONGO_PASS = "PASSWORD"


def check_dir():
    dirs = ["./file", "./img", "./audio", "./video"]
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
