from datetime import datetime
from typing import Optional
import uuid

from fastapi import FastAPI, Request
from pydantic import BaseModel
import asyncio
from feishu_agent import create_skills_based_agent
app = FastAPI(title="IT Agent Backend")

class MessageRequest(BaseModel):
    user_id: Optional[str] = None
    chat_id: str
    text: str

class MessageResponse(BaseModel):
    reply: str
# ---------- 工具函数 ----------
def generate_ticket_id() -> str:
    """生成工单编号（UUID 短码）"""
    short_id = uuid.uuid4().hex[:8].upper()
    return f"TK-{short_id}"

def get_current_time() -> str:
    """获取当前时间字符串（精确到分钟）"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")



@app.post("/agent/handle")
async def handle_ticket(req: MessageRequest):
    """处理工单并回复"""
    # body = await req.json()
    # print("收到请求体:", body)  # 打印实际内容
    try:
        # TODO: 这里接入你现有的Agent
        text = req.text
        user_id = req.user_id
        chat_id = req.chat_id
        reply = await create_skills_based_agent(text)
        # 2. 生成系统字段
        ticket_id = generate_ticket_id()
        created_time = get_current_time()
        # 模拟回复
        #reply = f"收到工单: {text}\n已创建并分派给IT组"
        # 提取需要的字段
    #     category = reply.fault_category
    #     solution = reply.solution
    #     user_query = reply.user_query   
    #     confidence = reply.confidence
        
    #     structured_reply = (
    # f"✅ 已为您创建工单 **{ticket_id}**\n"
    # f"用户问题：{user_query}\n"
    # f"📅 创建时间：{created_time}\n"
    # f"🔧 故障分类：{category}\n"
    # f"📝 解决方案：\n{solution}\n\n"
    # f"本回答的置信度为{confidence}，请根据实际情况酌情判断。"
    # f"如问题未解决，请回复“人工”转接技术支持。")
 
        return reply
        
        
    except Exception as e:
        print(f"处理出错: {e}")

