import asyncio
import re
from datetime import datetime
from typing import List
import os
import time
from typing import Optional, Union
import jieba
import numpy as np

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from wechaty import (
    Contact,
    FileBox,
    Message,
    Wechaty,
    ScanStatus,
    Room,
    get_logger,
    MessageType,
    Friendship,
    FriendshipType
)

from quiz import getVerifyCode

from pymongo import MongoClient
import atexit
from sshtunnel import SSHTunnelForwarder

from utils import *

# ###########正则#############
import regex as re



# 调整环境变量
os.environ['WECHATY_PUPPET'] = "wechaty-puppet-service"
os.environ['WECHATY_PUPPET_SERVICE_TOKEN'] = "xxxxxxxxxxxxxxxxxxxxxx"

    
log = get_logger('RoomBot')


server = SSHTunnelForwarder(MONGO_HOST,
    ssh_password=MONGO_PASS,
    ssh_username=MONGO_USER,
    remote_bind_address=('127.0.0.1', 27017))
server.start()


def shutdown():
    server.stop()

atexit.register(shutdown)

client = MongoClient('127.0.0.1', server.local_bind_port)



# # 管理入群
# collection1 = client["bot"]["room_invite"]
# # 管理此时群中信息
# # collection2 = client["bot"]["room_in"]
# # 管理消息信息
# collection2 = client["bot"]["message"]
# # 管理user信息
# collection3 = client["bot"]["user"]

# Baidu API:
# 获取access token
token = fetch_token()
# 拼接图像审核url
image_url = IMAGE_CENSOR + "?access_token=" + token
# 拼接文本审核url
text_url = TEXT_CENSOR + "?access_token=" + token



# aggregating room_bot

async def put_in_room(contact, room):
    log.info('Bot' + 'put_in_room("%s", "%s")' % (contact.name, await room.topic()))
    # try:
    #     await room.add(contact)
    #     # scheduler = AsyncIOScheduler()
    #     # # x = lambd
    #     # scheduler.add_job(lambda : await room.say(f'Welcome {contact.name}'))
    #     # scheduler.start()
    #     await room.say(f'Welcome {contact.name}')
    # except Exception as e:
    #     log.exception(e)
    await room.add(contact)
    await room.say(f'Welcome {contact.name}')


async def get_out_room(contact, room):
    log.info('Bot' + 'get_out_room("%s", "%s")' % (contact, room))
    try:
        await room.say('You said "ding" in my room, I will remove you out.')
        await room.delete(contact)
    except Exception as e:
        log.exception('get_out_room() exception: ', e)


async def regex_filter(msg: Message, from_contact: Contact):
    '''
    正则匹配模块：
    1. 匹配`淘口令`
    2. 匹配`加QQ`类广告
    3. 匹配`加微信`类广告
    4. 匹配`身份证号码`
    5. 匹配`身份证/密码`得敏感词汇
    6. 匹配`汇款`等敏感语句

    '''
    regex = [r'([\p{Sc}])\w{8,12}([\p{Sc}])',
             r'(?:[加qQ企鹅号码\s]{2,}|[群号]{1,})(?:[\u4e00-\u9eff]*)(?:[:，：]?)([\d\s]{6,})',
             r'(?:[加+微＋+➕薇？vV威卫星♥❤姓xX信]{2,}|weixin|weix)(?:[，❤️.\s]?)(?:[\u4e00-\u9eff]?)(?:[:，：]?)([\w\s]{6,})',
             r'(^[1-9]\d{5}(18|19|([23]\d))\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)|(^[1-9]\d{5}\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{3}$)',
             r'身份证号码|(?i)(银行卡|账号|QQ)密码',
             r'(微信|支付宝|银行|账户|银行卡|卡)+[\s\S]*([打钱]|[转账]|[汇款])+[\s\S]*[0-9]*'
             ]

    # print("enter regex")
    reply = ['识别为淘口令',
             '请不要在群内发QQ广告' + f'@{from_contact.name}',
             '请不要在群内发wx广告' + f'@{from_contact.name}',
             '请保护好个人敏感信息' + f'@{from_contact.name}',
             '请保护好个人敏感信息',
             '⚠️谨防受骗⚠️'
             ]

    flag = 0
    for i in range(len(regex)):
        r = re.compile(regex[i])
        if re.search(r, msg.text()):
            await msg.say(reply[i])
            flag = 1
            print("1")
        else:
            continue

    if flag == 0:
        print("正则匹配没毛病")
    return flag


async def dict_filter(msg: Message, from_contact:Contact):
    file_name = ["./data/政治.txt",
                 "./data/色情.txt",
                 "./data/广告.txt",
                 "./data/敏感词.txt",
                 "./data/暴恐.txt"]
    warning = ["不当政治言论", "色情信息", "广告", "敏感信息", "暴力恐怖"]
    words = jieba.cut(msg.text(), cut_all = False)
    words = list(words)
    words = np.array(words)
    tag = 0     #记录有无违规信息
    temp = 0

    atrocious_list = []

    for k in file_name:
        flag = 0 #针对每一种具体类别记录有无违规信息
        with open(k, 'r', encoding='utf-8') as fr:
            frrd = np.array(fr.readlines())
            for i in frrd:
                i = i.strip()
                for j in words:
                    if i == j:
                        flag = 1
                        tag = 1
        if flag:
            print("内容包含" + warning[temp])
            atrocious_list.append(warning[temp])
        temp = temp + 1

    if tag == 0:
        print("字典检测没毛病")
    else:
        await msg.say(f"亲爱的用户@{from_contact.name}，即便不在群中也不能违规，你的言语违规，进行一次警告")
        admolish_sentence = "你触犯了："
        for i in atrocious_list:
            admolish_sentence += i + ','
        await msg.say(admolish_sentence)

    return tag


async def api_filter(msg: Message, from_contact: Contact):
    flag = 0
    if msg.type() == MessageType.MESSAGE_TYPE_TEXT:
        result = request(text_url, urlencode({'text': msg.text()}))
        result = json.loads(result)
        if result['conclusion'] == '不合规' or '疑似':
            try:
                flag = 1
                word = result['data'][0]['msg']
                await msg.say(word)
                await msg.say(f"用户@{from_contact.name}违规")
            except Exception as e:
                print("合规")
                flag = 0

    elif msg.type() == MessageType.MESSAGE_TYPE_IMAGE:
        img = await msg.to_file_box()
        if not os.path.exists(f'./img/{img.name}'):
            await img.to_file(f'./img/{img.name}')
        result = request(image_url, urlencode({'image': base64.b64encode(read_file(f'./img/{img.name}'))}))
        result = json.loads(result)
        if result['conclusion'] == '不合规' or '疑似':
            try:
                flag = 1
                word = result['data'][0]['msg']
                await msg.say(word)
                await msg.say(f"用户@{from_contact.name}违规")
            except Exception as e:
                print('合规')
                flag = 0

    if flag == 0:
        print("api检测没毛病")
    return flag



async def warnandcheck(from_contact: Contact, room: Room, collection):

    await room.say(f"亲爱的群友@{from_contact.name}，你的有违规行为，进行一次警告")
    warning_times = warning_user(collection, from_contact)
    if warning_times:
        await room.say(f"您@{from_contact.name}已经被警告{warning_times}次")
    else:
        await room.say(f"您{from_contact.name}已经违规次数已达上限，即将将您移出群进行冷静")
        await room.delete(from_contact)
        await from_contact.say("请冷静5分钟")
        update(collection, from_contact.contact_id, "time_leave_room", time.time())
        update(collection, from_contact.contact_id, "remove", 1)


async def savecontent(msg: Message, from_contact: Contact, room: Room, collection):
    if room == None:
        return
    inserted_msg_dict = {"_id": msg.message_id, "wxid": from_contact.contact_id, "content": "", "type": 0, "time": 0}

    if msg.type() == MessageType.MESSAGE_TYPE_TEXT:
        # 文字类型的messgae为1
        inserted_msg_dict["type"] = 1
        inserted_msg_dict["content"] = msg.text()

    elif msg.type() == MessageType.MESSAGE_TYPE_IMAGE:
        img = await msg.to_file_box()
        await img.to_file(f'./img/{img.name}')

        # 图片类型的messgae为2
        inserted_msg_dict["type"] = 2
        inserted_msg_dict["content"] = f"./img/{img.name}"

    elif msg.type() == MessageType.MESSAGE_TYPE_AUDIO:
        audio = await msg.to_file_box()
        await audio.to_file(f'./audio/{audio.name}')

        # 音频类型的messgae为3
        inserted_msg_dict["type"] = 3
        inserted_msg_dict["content"] = f"./audio/{audio.name}"

    elif msg.type() == MessageType.MESSAGE_TYPE_VIDEO:
        video = await msg.to_file_box()
        await video.to_file(f'./video/{video.name}')

        # 视频类型的messgae为4
        inserted_msg_dict["type"] = 4
        inserted_msg_dict["content"] = f"./video/{video.name}"

    elif msg.type() == MessageType.MESSAGE_TYPE_ATTACHMENT:
        file = await msg.to_file_box()
        await file.to_file(f'./file/{file.name}')

        # 文件类型的messgae为5
        inserted_msg_dict["type"] = 5
        inserted_msg_dict["content"] = f"./file/{file.name}"

    elif msg.type() == MessageType.MESSAGE_TYPE_CONTACT:

        # contact类型的messgae为6
        inserted_msg_dict["type"] = 6
        inserted_msg_dict["content"] = f"contact"

    elif msg.type() == MessageType.MESSAGE_TYPE_EMOTICON:

        # EMOTICON类型的messgae为7
        inserted_msg_dict["type"] = 7
        inserted_msg_dict["content"] = f"EMOTICON"

    else:
        # 其他类型的msg为8
        inserted_msg_dict["type"] = 8
        inserted_msg_dict["content"] = "OTHER"

    inserted_msg_dict["time"] = time.time()
    if insert(collection, msg.message_id, inserted_msg_dict):
        print(f"完成如下内容的记录保存{str(inserted_msg_dict)}")
    else:
        print("记录失败")


async def calculatespeak(msg: Message, from_contact: Contact, room: Room, collection):
    print("对用户发出信息进行对应操作")
    if room == None:
        return
    find_res = find(collection=collection, id=from_contact.contact_id)
    update(collection, from_contact.contact_id, "speak_num", find_res["speak_num"] + 1)

    if msg.message_type() == MessageType.MESSAGE_TYPE_IMAGE:
        update(collection, from_contact.contact_id, "imgs_num", find_res["imgs_num"] + 1)


async def checkandinvite(from_contact: Contact, room: Room, collection_user, onlyappend_info=False):
    print("检查并邀请")
    res = find(collection_user, from_contact.contact_id)

    if res == False:
        inserted_dict = {"_id": from_contact.contact_id, "time_in_ststem": time.time(), "time_in_room": 0,
                         "time_leave_room": 0, "remove": 0, "speak_num": 0, "imgs_num": 0, "warning": 0}
        insert(collection_user, from_contact.contact_id, inserted_dict)
    elif int(res["time_leave_room"]) < int(res["time_in_room"]):
        topic = await room.topic()
        log.info('Bot' + f'onMessage: sender has already in room{topic}')
        await room.say(f'您 @{from_contact.name} 已经在群聊 "{topic}"中！')
        await from_contact.say(
            '不需要再次申请入群，因为您已经在群"{}"中'.format(topic))
        return

    if not onlyappend_info:
        log.info('Bot' + 'onMessage: add sender("%s") to dingRoom("%s")' % (
            from_contact.name, room.topic()))
        await put_in_room(from_contact, room)
        await from_contact.say('已经您拉入群中')

    update(collection_user, from_contact.contact_id, "time_in_room", time.time())
    update(collection_user, from_contact.contact_id, "remove", 0)
    update(collection_user, from_contact.contact_id, "warning", 0)

    if onlyappend_info:
        print("已添加新用户到user数据库中")




class MyWechatBot(Wechaty):
    """
    微信机器人类，包含所需要的基本类属性
    属性：
        1. busy: 匆忙特征
        2. busy_auto_reply_comment: 匆忙时回答内容
        3.
        4.
        5.
    """

    def __init__(self):
        super().__init__()

        print("Initializing the Wechaty bot.")
        self.busy = False
        self.busy_auto_reply_comment = "目前入群功能正在维护中，请耐心等待调试过程"
        # self.verify_info = {}
        self.boton_quit = {}
        # 管理入群
        self.collection1 = client["bot"]["room_invite"]
        # 管理消息信息
        self.collection2 = client["bot"]["message"]
        # 管理user信息
        self.collection3 = client["bot"]["user"]

        self.checkroom_FLAG = 0

        check_dir()




        # TODO:


    async def check_room(self):
        room = await self.Room.find('新测试群')

        print(f"检查room{room.topic()}")
        await room.say("机器人已上线，正在做初始化工作")
        current_members = await room.member_list()
        cur_member_id = []
        for member in current_members:
            cur_member_id.append(member.contact_id)
            if find(self.collection3, member.contact_id) == False:
                await checkandinvite(from_contact=member, room=room, collection_user=self.collection3, onlyappend_info=True)

        for previous_user in self.collection3.find():
            if previous_user["_id"] not in cur_member_id:
                print("此前的群友{}已经离开群".format(previous_user["_id"]))
                update(self.collection3, previous_user["_id"], "time_leave_room", time.time())
            # previous_user_dict.append(previous_user["_id"])

        # for privious_user in


    async def on_friendship(self, friendship: Friendship):
        print("received friendship")

        administrator = bot.Contact.load('wxid_qgho9l2kdha311')
        await administrator.ready()


        contact = friendship.contact()
        await contact.ready()

        log.info('Bot' + f'- INFO - receive friendship message from {contact.name}')
        log_msg = f'receive "friendship" message from {contact.name}'
        await administrator.say(log_msg)

        if friendship.type() == FriendshipType.FRIENDSHIP_TYPE_RECEIVE:
            print(friendship.hello())
            log.info('Bot' + f'- INFO - automatically accepted because it is a easy-bot.')
            await friendship.accept()
            # if want to send msg, you need to delay sometimes

            print('waiting to send message ...')
            await asyncio.sleep(3)
            await contact.say('hey there\n 请发送 #帮助 获取进群提示')
            print('after accept ...')

            # if friendship.hello() == 'ding':
            #     log_msg = 'accepted automatically because verify messsage is "ding"'
            #     print('before accept ...')
            #     await friendship.accept()
            #     # if want to send msg, you need to delay sometimes
            #
            #     print('waiting to send message ...')
            #     await asyncio.sleep(3)
            #     await contact.say('hello from wechaty ...')
            #     print('after accept ...')
            # else:
            #     log_msg = 'not auto accepted, because verify message is: ' + friendship.hello()

        elif friendship.type() == FriendshipType.FRIENDSHIP_TYPE_CONFIRM:
            log_msg = 'friend ship confirmed with ' + contact.name

        # print(log_msg)
        await administrator.say(log_msg)




    # async def on_scan(qrcode: str, status: ScanStatus, _data,):
    #     """
    #     Scan Handler for the Bot
    #     """
    #     print('Status: ' + str(status))
    #     print('View QR Code Online: https://wechaty.js.org/qrcode/' + qrcode)

    async def on_scan(self, status: ScanStatus, qr_code: Optional[str] = None,
                      data: Optional[str] = None):
        contact = self.Contact.load(self.contact_id)
        print(f'user <{contact}> scan status: {status.name} , '
              f'qr_code: {qr_code}')

    # async def on_login(user: Contact):
    #     """
    #     Login Handler for the Bot
    #     """
    #     print(user)
    #     # TODO: To be written

    async def on_login(self, contact: Contact):
        msg = contact.payload.name + ' logined'
        log.info('bot ' + msg)
        await contact.say(msg)

        # msg = "setting to manage_ding_room() after 3 seconds..."
        log.info('Bot' + msg)
        print(self.user_self())
        await contact.say(msg)

        await self.check_room()
        # await manage_ding_room(self)


    def on_error(self, payload):
        log.info(str(payload))


    def on_logout(self, contact: Contact):
        log.info('Bot %s logouted' % contact.name)


    async def on_room_join(self, room: Room, invitees: List[Contact],
                           inviter: Contact, date: datetime):
        log.info('Bot' + 'EVENT: room-join - Room "%s" got new member "%s", invited by "%s"' %
                 (await room.topic(), ','.join(map(lambda c: c.name, invitees)), inviter.name))
        print('bot room-join room id:', room.room_id)

        # 保护
        if room.room_id not in bot_owner_room_id_list:
            return


        if inviter.contact_id != self.contact_id and inviter.contact_id not in owner_contact_id_list:
            await room.say("规则1：邀请权限目前只开放给bot，请勿随意拉人")
            await room.say(f"被邀请者@{invitees[0].name}可以通过向bot私发 #帮助 寻找进群策略")
            scheduler = AsyncIOScheduler()
            for i in invitees:
                scheduler.add_job(room.delete, args=[i])
            scheduler.start()

            # 先暂停这个功能
            await warnandcheck(inviter, room, self.collection3)


            # await room.say(f"警告@{inviter.name}")
            # warning_times = warning_user(collection2, inviter)
            # if warning_times:
            #     await room.say(f"您@{inviter.name}已经被警告{warning_times}次")
            # else:
            #     await room.say(f"您{inviter.name}已经违规次数已达上限，即将将您移出群进行冷静")
            #     await room.delete(inviter)
            #     await inviter.say("请冷静3小时")
            #
            #     update(collection2, inviter.contact_id, "time_last_warning", time.time())



        else:
            await checkandinvite(invitees[0], room, collection_user=self.collection3, onlyappend_info=True)
            topic = await room.topic()
            await room.say(f'welcome to "{topic}", @{invitees[0].name}!')


    async def on_room_leave(self, room: Room, leavers: List[Contact],
                            remover: Contact, date: datetime):
        log.info('Bot' + 'EVENT: room-leave - Room "%s" lost member "%s"' %
                 (await room.topic(), ','.join(map(lambda c: c.name, leavers))))
        topic = await room.topic()
        name = leavers[0].name if leavers[0] else 'no contact!'

        # 在botonquit中添加用户离开信息
        print("在botonquit中添加用户离开信息")
        if not self.boton_quit.__contains__(room.room_id):
            self.boton_quit[room.room_id] = []
        self.boton_quit[room.room_id].append(leavers[0].contact_id)

        # TODO:需要添加此时用户离开群聊时的time_leave字段，同时在进群时需要把time_leave, remove字段更新为0


        if remover.contact_id == leavers[0].contact_id:
            await room.say(f'我们的群友@{leavers[0].name}自行离开了群')
            await leavers[0].say("您自行离开了群，如需再入群，请输入 #帮助 查询最新入群方法")
            update(collection=self.collection3, id=leavers[0].contact_id, field="time_leave_room", value=time.time())
            # update(collection=self.collection3, id=leavers[0].contact_id, field="remove", value=0)


        elif remover.contact_id != self.contact_id:
            await room.say(f'管理员@{remover.name}把用户{leavers[0].name}移出群聊')
            # await room.say(f'只有我可以删人，警告一次@{remover.name}')
            await leavers[0].say(f"你出于某种原因被管理员移出群聊{topic}了，从现在开始存在5分钟的冷静期")
            update(collection=self.collection3, id=leavers[0].contact_id, field="time_leave_room", value=time.time())
            update(collection=self.collection3, id=leavers[0].contact_id, field="remove", value=1)


        else:
            await room.say(f'Bot将用户@{leavers[0].name}移出群')


    async def on_room_topic(self, room: Room, new_topic: str, old_topic: str,
                            changer: Contact, date: datetime):
        try:
            log.info('Bot' + 'EVENT: room-topic - Room "%s" change topic from "%s" to "%s" by member "%s"' %
                     (room, old_topic, new_topic, changer))
            await room.say('room-topic - change topic from "{0}" to "{1}" '
                           'by member "{2}"'.format(old_topic, new_topic, changer.name))
        except Exception as e:
            log.exception(e)


    async def on_message(self, msg: Message):
        """
        listen for msg event.
        :param msg: received msg.
        :return: none
        """

        # msg
        # attrs:
        # message_id(str) '3037907331459016207'
        # from_id(str) 'wxid_qgho9l2kdha311'
        # mention_ids(list)
        # room_id(str)  ''
        # text(str) '1'
        # timestamp(int) 1620493045
        # to_id(str) 'wxid_vj8wsjhms91j22'


        # busy-bot: 可以输入特定指令使得机器人不会进行自动回答，可以用于进群验证时的维护状态


        from_contact = msg.talker()
        # attrs:
        # name(str) 'ＫＩＥＲＡＮ．'
        # contact_id(str) 'wxid_qgho9l2kdha311'
        # address ''
        # alias ''
        # avatar 'https://wx.qlogo.cn/mmhead/ver_1/NFn8dpgY2taGWzz0jOnZFZ2rMsiaoINkFRuLDRtxTKyFREY56tIrWCXmdHMicB7cQxK7bJXqiajadVnicaM9CrAh0z1krDEpMs8AKEdMoHjaXvw/0'
        # city ''
        # friend True
        # gender 1
        # signature '短期计划者'
        # weixin 'kieran00000'

        text = msg.text()

        room = msg.room()

        to = msg.to()
        # attrs:
        # name(str) '随便取个名吧'
        # contact_id(str) 'wxid_vj8wsjhms91j22'
        # address ''
        # alias ''
        # avatar ''
        # city ''
        # friend True
        # gender 0
        # signature ''
        # weixin ''

        print(msg.type())

        if msg.is_self():
            return

        await savecontent(msg, from_contact, room, self.collection2)

        await calculatespeak(msg, from_contact, room, self.collection3)

        # if msg.type() == MessageType.MESSAGE_TYPE_AUDIO:
        #     audio = await msg.to_file_box()
        #     # save the image as local file
        #     await audio.to_file(f'./{audio.name}')

        # if msg.type() == MessageType.MESSAGE_TYPE_ATTACHMENT:
        #     file = await msg.to_file_box()
        #     await file.to_file(f"./{file.name}")
        #     print("保存文件成功")

        if msg.type() == MessageType.MESSAGE_TYPE_RECALLED:
            # recalledMessage = await msg.to_recalled()
            # 方法有错误，下面自己手写debug得到。

            msg_text = msg.text()
            # recalledMessage = self.Message.load(message_id=msg_text)
            # await recalledMessage.ready()
            origin_message_id = re.findall(r'<newmsgid>(.*?)</newmsgid>', msg_text)[0]

            # recalledMessage = self.Message.find_all(message_id=origin_message_id)
            recalledMessage = self.Message.load(message_id=origin_message_id)
            await recalledMessage.ready()
            log.info('Bot' + f'EVENT: Detect Recalled text : {recalledMessage.text()} . FROM {from_contact.contact_id}')
            print(f"Recalled msg is {recalledMessage.text()}")





        # 此处的if
        if room == None and to.contact_id == self.contact_id:
            # When someone try to contact with the bot
            if text == '#状态':
                msg = 'busy' if self.busy else 'free'
                await from_contact.say(
                    f'My status: {msg}')
                if self.busy == True:
                    await from_contact.say(self.busy_auto_reply_comment)

            elif text == '#开启':
                # Problem: the talker should be an authentic wechat user.
                self.busy = False
                await from_contact.say('关闭自动回复')

            elif text == '#关闭':
                # Problem: the talker should be an authentic wechat user.
                self.busy = True
                await from_contact.say('打开自动回复.')

            elif self.busy == False:
                # 添加基本的进群验证功能。
                if msg.text() == 'ding':
                    await from_contact.say('dong')
                    # await from_contact.say('目前只能进行ding的回复，请继续等待后续开发😂')

                if msg.text() == '#帮助':
                    await from_contact.say('1. 发送 \'#加群\' 给bot，bot会发送给用户对应的验证码图片\n'
                                           '2. 发送 \'#验证 XXXX\' 给bot，bot会完成验证并给予答复，拉人接口暂时还未完善\n'
                                           '3. 发送 \'ding\' 给bot，bot会答复dong')

                elif msg.text().startswith('#加群'):

                    find_result = find(self.collection3, from_contact.contact_id)
                    if find_result != False and find_result['remove'] != 0:
                        passed_time = time.time() - find_result['time_leave_room']
                        if passed_time < 300:
                            await from_contact.say(f"你的冷静期还未结束。还剩余{300 - int(passed_time)}秒")
                            return

                    inserted_dict = {"_id": from_contact.contact_id, "quiz_ans": "", "quiz_time": 0}
                    insert(self.collection1, from_contact.contact_id, inserted_dict)

                    await from_contact.say('请稍等验证码生成,并在60s内完成回答')

                    img, code = getVerifyCode()

                    update(self.collection1, from_contact.contact_id, "quiz_ans", code)
                    update(self.collection1, from_contact.contact_id, "quiz_time", time.time())
                    # 为了防止用户连续两次进行请求

                    # self.verify_info[from_contact.contact_id] = code

                    img = FileBox.from_file('./temp_verify.jpg')
                    await from_contact.say(img)
                    # print(self.verify_info[from_contact.contact_id])
                    print(code)

                    # await from_contact.say("目前进群功能仍在开发中")
                    # await from_contact.say('请耐心等待开发')


                elif msg.text() == '#我是你爹':
                    await from_contact.say("主人sama，马上把您拉上群")


                    try:
                        dingRoom = await self.Room.find('新测试群')
                        if dingRoom:
                            log.info('Bot' + 'onMessage: got dingRoom: "%s"' % await dingRoom.topic())
                            await checkandinvite(from_contact=from_contact, room = dingRoom, collection_user=self.collection3)
                            #
                            #
                            # if self.boton_quit.__contains__(dingRoom.room_id):
                            #     boton_quit_list = self.boton_quit[dingRoom.room_id]
                            # else:
                            #     boton_quit_list = []
                            #
                            # if from_contact.contact_id not in boton_quit_list and await dingRoom.has(from_contact):
                            #     topic = await dingRoom.topic()
                            #     log.info('Bot' + 'onMessage: sender has already in dingRoom')
                            #     # await dingRoom.say('I found you have joined in room "{0}"!'.format(topic), talker)
                            #     await dingRoom.say(f'您 @{from_contact.name} 已经在群聊 "{topic}"中！')
                            #     await from_contact.say(
                            #         '不需要再次申请入群，因为您已经在群"{}"中'.format(topic))
                            # else:
                            #     inserted_dict = {"_id": from_contact.contact_id, "time_in": time.time(), "warning": 0,
                            #                      "time_last_warning": 0}
                            #     insert(collection2, from_contact.contact_id, inserted_dict)
                            #     update(collection2, from_contact.contact_id, "warning", 0)
                            #     update(collection2, from_contact.contact_id, "time_last_warning", 0)
                            #
                            #
                            #     if from_contact.contact_id in boton_quit_list:
                            #         self.boton_quit[dingRoom.room_id].remove(from_contact.contact_id)
                            #     log.info('Bot' + 'onMessage: add sender("%s") to dingRoom("%s")' % (
                            #         from_contact.name, dingRoom.topic()))
                            #     await put_in_room(from_contact, dingRoom)
                            #     await from_contact.say('已经您拉入群中')


                    except Exception as e:
                        log.exception(e)



                elif msg.text().startswith('#验证'):
                    user_verify_code = msg.text()[4:]
                    print(user_verify_code)

                    find_result = find(self.collection1, from_contact.contact_id)
                    # if not self.verify_info.__contains__(from_contact.contact_id):
                    if find_result == False:
                        await from_contact.say('并未进行加群请求!，请先发送 #加群 至机器人获取专属验证码')
                        return

                    if time.time() - find_result['quiz_time'] > 60:
                        # expired_code = self.verify_info.pop(from_contact.contact_id)
                        delete(self.collection1, from_contact.contact_id)
                        print(f'previous code has benn expired')
                        await from_contact.say("超时未回答正确验证码信息，请重新发送 #加群 再进行尝试")

                    elif user_verify_code == find_result['quiz_ans']:

                        # TODO: 需不需要再在roominvite中删除？
                        delete(self.collection1, from_contact.contact_id)
                        print(f"在room_invite中删除一认证用户{from_contact.name}")


                        await from_contact.say("通过测试，后续会将您拉入群中")
                        # put_in_room()
                        # await from_contact.say("目前进群功能仍在开发中")



                        try:
                            dingRoom = await self.Room.find('新测试群')
                            if dingRoom:
                                log.info('Bot' + 'onMessage: got dingRoom: "%s"' % await dingRoom.topic())
                                await checkandinvite(from_contact=from_contact, room=dingRoom,
                                                    collection_user=self.collection3)

                                # if self.boton_quit.__contains__(dingRoom.room_id):
                                #     boton_quit_list = self.boton_quit[dingRoom.room_id]
                                # else:
                                #     boton_quit_list = []
                                #
                                # if from_contact.contact_id not in boton_quit_list and await dingRoom.has(from_contact):
                                #     topic = await dingRoom.topic()
                                #     log.info('Bot' + 'onMessage: sender has already in dingRoom')
                                #     # await dingRoom.say('I found you have joined in room "{0}"!'.format(topic), talker)
                                #     await dingRoom.say(f'您 @{from_contact.name} 已经在群聊 "{topic}"中！')
                                #     await from_contact.say(
                                #         '不需要再次申请入群，因为您已经在群"{}"中'.format(topic))
                                # else:
                                #     if from_contact.contact_id in boton_quit_list:
                                #         self.boton_quit[dingRoom.room_id].remove(from_contact.contact_id)
                                #
                                #     inserted_dict = {"_id": from_contact.contact_id, "time_in": time.time(),
                                #                      "warning": 0, "time_last_warning": 0}
                                #     insert(collection2, from_contact.contact_id, inserted_dict)
                                #     update(collection2, from_contact.contact_id, "warning", 0)
                                #     update(collection2, from_contact.contact_id, "time_last_warning", 0)
                                #     print("完成新人信息的插入")
                                #
                                #     log.info('Bot' + 'onMessage: add sender("%s") to dingRoom("%s")' % (
                                #         from_contact.name, dingRoom.topic()))
                                #     await put_in_room(from_contact, dingRoom)
                                #     await from_contact.say('已经您拉入群中')

                        except Exception as e:
                            log.exception(e)


                    else:
                        # 输入失败
                        await from_contact.say("验证失败，请再次尝试。")
                # 正常文字信息
                else:
                    if await regex_filter(msg, from_contact) != 0:
                        print("正则匹配得到")
                        # print("是这里吗？")
                        return
                    elif await dict_filter(msg, from_contact) != 0:
                        # print("regex passed")
                        print("字典检测得到")
                    # elif
                    # TODO:
                    elif await api_filter(msg, from_contact) != 0:
                        print("api匹配得到")
                        # print("regex passed")
                        # print("dict passed")

                    # else:
                        # print("regex passed")
                        # print("dict passed")
                        # print("api passed")



            else:
                await from_contact.say(self.busy_auto_reply_comment)

        # Room talk
        elif room.room_id == '23402005339@chatroom':
            print(1)
            if msg.text() == 'ding':
                await msg.say('dong')
                # await msg.say('目前只能进行ding的回复，请继续等待后续开发😂')

            else:
                # 正常的群中对话信息
                if await regex_filter(msg, from_contact) != 0:
                    print("正则匹配得到")
                    if from_contact.contact_id in owner_contact_id_list:
                        await room.say("管理员测试中")
                        return
                    await warnandcheck(from_contact, room, self.collection3)
                    return

                elif await dict_filter(msg, from_contact) != 0:
                    print("字典得到")
                    if from_contact.contact_id in owner_contact_id_list:
                        await room.say("管理员测试中")
                        return
                    await warnandcheck(from_contact, room, self.collection3)
                    return

                elif await api_filter(msg, from_contact) != 0:
                    print("API完成检测")
                    if from_contact.contact_id in owner_contact_id_list:
                        await room.say("管理员测试中")
                        return
                    await warnandcheck(from_contact, room, self.collection3)
                    return
                # elif
                # TODO:


async def main():
    """
    Async Main Entry
    """
    #
    # Make sure we have set WECHATY_PUPPET_SERVICE_TOKEN in the environment variables.
    #
    if 'WECHATY_PUPPET_SERVICE_TOKEN' not in os.environ:
        print('''
            Error: WECHATY_PUPPET_SERVICE_TOKEN is not found in the environment variables
            You need a TOKEN to run the Python Wechaty. Please goto our README for details
            https://github.com/wechaty/python-wechaty-getting-started/#wechaty_puppet_service_token
        ''')

    global bot
    bot = MyWechatBot()
    await bot.start()
    print('[Python Wechaty] Ding Dong Bot started.')


asyncio.run(main())
