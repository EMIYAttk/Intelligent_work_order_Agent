import asyncio
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from retrieval_tools import retrieve_knowledge, RETRIEVAL_TOOLS
from skills_agent_backup import SkillMiddleware, SkillState,load_skill,LoggingMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from env_utils import OPENAI_MODEL_NAME, OPENAI_API_KEY, OPENAI_BASE_URL
from skills_loader import SKILLS
from langchain.agents import create_agent, AgentState
from langchain_core.messages import SystemMessage, ToolMessage
import os
# 1. 设置离线模式，禁止联网检查更新，这是解决卡顿的核心
os.environ['HF_HUB_OFFLINE'] = '1'

# 定义工单结构化输出模型
class TicketOutput(BaseModel):
    """IT工单结构化输出"""
    fault_category: Literal["hardware_printer", "hardware_network", "software_os", "software_account", "other"] = Field(
        description="故障分类，必须从指定枚举中选择,如果无法匹配任何选项，使用 'other'"
    )
    solution: str = Field(
        description="基于技能加载和知识库检索整理后得出的处理步骤，清晰列出.如果分类为 'other'，则直接使用助手的统一回复内容"
    )
    user_query: str = Field(
        description="用户原始问题描述"
    )
    confidence: Optional[float] = Field(
        default=0.8,
        description="模型对解决方案的置信度，范围0-1，这个数值可以基于知识库检索到的文档和用户输入的距离来计算。对于 'other' 分类，置信度设置为0.0.",
        ge=0, le=1
    )
# 2. 定义新的输出模型，将工单列表作为核心字段
class MultiTicketOutput(BaseModel):
    """多工单结构化输出模型"""
    original_user_query: str = Field(
        description="用户的完整原始问题描述"
    )
    tickets: List[TicketOutput] = Field(
        description="从用户问题中提取并生成的工单列表。如果用户问题包含多个独立故障，请为每个故障生成一个工单项。"
    )
    
local_tools = {
    skill["name"]: skill["tools"]
    for skill in SKILLS
    if skill["tools"]  # 只有当工具列表非空时才加入
}

model = ChatOpenAI(model="qwen3.5-35b-a3b", # 使用 OPENAI_MODEL_NAME qwen3.5-flash                      
                      base_url=OPENAI_BASE_URL,
                      api_key=OPENAI_API_KEY,
                      extra_body={"enable_thinking": False},
                  )
model2 = ChatOpenAI(model="qwen3.5-flash", # 使用 OPENAI_MODEL_NAME qwen3.5-flash                      
                      base_url=OPENAI_BASE_URL,
                      api_key=OPENAI_API_KEY,
                      extra_body={"enable_thinking": False},
                  )
agent = create_agent(
        model,
        tools=[load_skill,retrieve_knowledge],  # 初始只暴露load_skill工具
        middleware=[SkillMiddleware(local_tools),LoggingMiddleware()],  #categorized_tools
        state_schema=SkillState,
        #response_format=ToolStrategy(TicketOutput),
        system_prompt="""
        
        你是一个专业的IT智能工单助手，负责处理员工提交的各种软硬件故障、网络问题、账号权限等工单。
        在你的初始上下文中已经提供了每个技能的名称和简要描述。
【核心工作流程】
当用户描述一个具体故障时，你必须按照以下两步执行：

1. **识别故障类型**  
   根据用户的问题内容，结合上述技能描述，判断最匹配的技能 ID（如 `hardware_printer`、`hardware_network`、`software_os`、`software_account`）。

2. **调用两个工具来获取真实消息**（两者都需要执行）：
   - 调用 `load_skill` 工具，参数为识别出的 `skill_id`，以加载该技能的完整处理能力。
   - 调用 `retrieve_knowledge` 工具，参数为 `skill_id`、用户问题的核心描述 `query`（建议10字以内关键词）、`top_k`（默认2），以获取该故障的具体处理步骤。

【调用示例】
假设用户说：“打印机卡纸了，纸张卡在出纸口附近”
- 识别 skill_id = "hardware_printer"
- 调用 `load_skill(skill_id="hardware_printer")`
- 调用 `retrieve_knowledge(skill_id="hardware_printer", query="打印机卡纸", top_k=2)`

【回复规范】
- 如果 `retrieve_knowledge` 返回了有效文档，请基于文档内容组织回答，按步骤清晰列出。
- 如果文档和用户问题之间存在较大的距离，请直接回复：“未在知识库中找到直接解决方案，建议您联系IT支持团队（分机号1234）。”

【注意事项】
- 不要跳过 `load_skill` 直接使用 `retrieve_knowledge`，因为 `load_skill` 会激活该技能所需的完整工具集或上下文。
- 如果用户的问题涉及多个技能（例如“打印机卡纸且电脑蓝屏”），优先处理最紧急或用户首先提到的故障.

【无法识别故障类型时的处理】
则请执行以下操作：
1. **不要调用任何工具**（不调用 load_skill，也不调用 retrieve_knowledge）
2. 直接回复以下统一消息：
   “抱歉，当前工单助手仅支持处理【打印机故障、网络问题、操作系统异常、账号权限等问题】。您描述的问题:用户的问题描述,不在服务范围内，请确认后重新提交，或联系人工客服（分机号1234）。”
 """
        

)
structuring_agent = create_agent(
    model=model2,  # 你使用的模型
    tools=[],     # 不需要任何工具
    system_prompt="""
你是一个工单信息提取助手。你的任务是从输入内容中提取关键信息，并按照指定的 JSON 格式输出。

输入内容是一个 IT 支持助手对用户问题的回复，其中已经包含了故障分类、解决方案等。


**工单生成规则**：
1. 推断故障类别（printer / network / os / account）
2. 提取解决方案的具体步骤（保持原有格式，不要自己编造）
3. 提取用户原始问题（如果输入中没有明确给出，请根据上下文合理推断）
4. 给出你对提取结果的置信度（0-1）

只输出结构化的结果，不要输出其他解释。
【特殊情况处理】
- 如果助手的回复中包含“不在服务范围内”或“无法处理”等明确拒绝的表述，则：
  - 将 `fault_category` 设为 "other"
  - 将 `solution` 字段直接复制助手的完整回复内容
  - 将 `confidence` 设为 0.0

- 否则，按正常流程提取分类、解决方案等。
""",
    response_format=ToolStrategy(TicketOutput)
)

async def create_skills_based_agent(query:str):
    
    res = await agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })
    #text = res["structured_response"]
    text = res["messages"][-1].content
    print(f"原始输出：{text}")
    structured_res = await structuring_agent.ainvoke({"messages": [{"role": "user", "content": text}]})
    
    structured_text = structured_res["structured_response"]
    
    
    print(f"结构化输出：{structured_text}")
    
    return structured_text

# print(res["messages"][-1].content)