import os
import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import asyncio
import httpx
from env_utils import FEISHU_APP_ID, FEISHU_APP_SECRET
from feishu_agent import create_skills_based_agent
import uuid
from datetime import datetime
import re

# ========== 配置区域 ==========
APP_ID = FEISHU_APP_ID      # 你的App ID
APP_SECRET = FEISHU_APP_SECRET   # 你的App Secret

# 存储token用于发送消息
CACHE_TOKEN = {"token": None, "expire": 0}

# ---------- 工具函数 ----------
def generate_ticket_id() -> str:
    """生成工单编号（UUID 短码）"""
    short_id = uuid.uuid4().hex[:8].upper()
    return f"TK-{short_id}"

def get_current_time() -> str:
    """获取当前时间字符串（精确到分钟）"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def get_category_color(category: str) -> str:
    colors = {
        "printer": "orange",
        "network": "blue",
        "os": "red",
        "account": "green",
        "other": "grey"
    }
    return colors.get(category, "blue")

def fill_card_template(card_dict, data):
    """递归替换卡片模板中的 {{key}} 占位符"""
    if isinstance(card_dict, dict):
        new_dict = {}
        for k, v in card_dict.items():
            if isinstance(v, str):
                new_value = v
                for placeholder, value in data.items():
                    new_value = new_value.replace('{{' + placeholder + '}}', str(value))
                new_dict[k] = new_value
            else:
                new_dict[k] = fill_card_template(v, data)
        return new_dict
    elif isinstance(card_dict, list):
        return [fill_card_template(item, data) for item in card_dict]
    else:
        return card_dict

async def get_tenant_access_token():
    """获取飞书API调用凭证"""
    import time
    if time.time() < CACHE_TOKEN["expire"] - 300:
        return CACHE_TOKEN["token"]
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "app_id": APP_ID,
            "app_secret": APP_SECRET
        })
        data = resp.json()
        CACHE_TOKEN["token"] = data["tenant_access_token"]
        CACHE_TOKEN["expire"] = time.time() + data["expire"]
        return data["tenant_access_token"]

async def send_message(chat_id: str, text: str, at_open_id: str = None):
    """发送文本消息"""
    token = await get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {"receive_id_type": "chat_id"}
    # 构建消息内容，如果需要 @ 用户，就在文本里加上 at 标签
    if at_open_id:
        # 注意这里的转义要写对
        text = f"<at user_id=\"{at_open_id}\"></at> {text}"
    body = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, params=params, json=body)
        print(f"发送结果: {resp.json()}")
        
async def send_card_message(chat_id: str, card_content: dict):
    """
    发送飞书卡片消息
    :param chat_id: 群聊或用户的 chat_id
    :param card_content: 卡片 JSON 字典（已填充好数据）
    """
    token = await get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {"receive_id_type": "chat_id"}
    body = {
        "receive_id": chat_id,
        "msg_type": "interactive",  # 卡片消息类型
        "content": json.dumps(card_content)  # 卡片 JSON 转为字符串
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, params=params, json=body)
        print(f"发送卡片结果: {resp.json()}")
        return resp.json()
    
# ========== 消息处理器 ==========
def do_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """
    收到消息时的回调函数
    data: 飞书推送的消息数据结构
    """
    print(f'[收到消息] {lark.JSON.marshal(data, indent=4)}')
    
    # 提取关键信息
    event = data.event
    message = event.message
    sender = event.sender
    
    # 只处理文本消息
    if message.message_type != "text":
        print("非文本消息，忽略")
        return
    
    # 解析消息内容（JSON字符串）
    content = json.loads(message.content)
    text = content.get("text", "")
    chat_id = message.chat_id
    open_id = sender.sender_id.open_id   # ✅ 修正：使用 open_id
    
    print(f"内容: {text}")
    print(f"用户 open_id: {open_id}")      # 输出 open_id
    print(f"群聊: {chat_id}")
    
    # 检查是否@机器人（通过mentions字段）
    mentions = message.mentions if message.mentions else []
    is_at_bot = len(mentions) > 0
    
    # 或者私聊也算
    # is_at_bot = True  # 测试时可以先全开
    
    if not is_at_bot:
        print("未@机器人，忽略")
        return
    
    # 清理@文本
    for mention in mentions:
        key = mention.key
        text = text.replace(key, "").strip()
    
    # 异步处理（避免阻塞SDK回调）
    asyncio.create_task(handle_ticket(text, open_id, chat_id))

#待修改，和fastapi的接口对接
async def handle_ticket(text: str, user_id: str, chat_id: str):
    """处理工单并回复"""
    try:
        # TODO: 这里接入你现有的Agent
        reply = await create_skills_based_agent(text)
        # 2. 生成系统字段
        ticket_id = generate_ticket_id()
        created_time = get_current_time()
        # 模拟回复
        #reply = f"收到工单: {text}\n已创建并分派给IT组"
        # 提取需要的字段
        category = reply.fault_category
        solution = reply.solution
        user_query = reply.user_query   
        confidence = reply.confidence
        
        structured_reply = (
    f"✅ 已为您创建工单 **{ticket_id}**\n"
    f"用户问题：{user_query}\n"
    f"📅 创建时间：{created_time}\n"
    f"🔧 故障分类：{category}\n"
    f"📝 解决方案：\n{solution}\n\n"
    f"本回答的置信度为{confidence}，请根据实际情况酌情判断。"
    f"如问题未解决，请回复“人工”转接技术支持。")
 
        # await send_message(chat_id, structured_reply,user_id)
        # #await send_message(chat_id, reply)
        # print("回复成功")
    # 准备工单数据（从结构化输出中获取）
        data = {
    "ticket_id": generate_ticket_id(),
    "category": reply.fault_category,
    "category_color": get_category_color(reply.fault_category),  # 自定义映射函数
    "created_time": get_current_time(),
    "user_query": reply.user_query,
    "solution": reply.solution,
    "confidence": f"{int(reply.confidence * 100)}%"
}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        json_path = os.path.join(script_dir, "card_template.json")
       # 加载模板并填充
        with open(json_path, "r", encoding="utf-8") as f:
            template = json.load(f)
        filled_card = fill_card_template(template, data)

      # 发送卡片
        await send_card_message(chat_id, filled_card)    
    except Exception as e:
        print(f"处理出错: {e}")
        await send_message(chat_id, "处理出错，请重试",user_id)

# ========== 启动 ==========
def main():
    # 构建事件处理器
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1) \
        .build()
    
    # 创建客户端
    cli = lark.ws.Client(
        APP_ID, 
        APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG
    )
    
    print(f"🚀 启动飞书机器人...")
    print(f"App ID: {APP_ID}")
    cli.start()

if __name__ == "__main__":
    main()