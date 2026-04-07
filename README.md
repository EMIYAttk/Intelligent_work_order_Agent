智能工单助手 - 基于 LangChain + ChromaDB + 飞书的 IT 运维 Agent
采用两阶段 Agent 架构（工具调用 + 结构化输出），实现故障知识库检索、工单自动生成与飞书卡片推送。支持多技能领域（打印机/网络/OS/账号），使用 BGE 中文嵌入模型，通过 FastAPI 解耦业务逻辑与消息网关。展示 RAG、工具调用、结构化输出、异步事件处理等 Agent 核心能力。

演示视频在项目首页文件夹的demo.mp4：



![点击观看演示视频](https://raw.githubusercontent.com/EMIYAttk/Intelligent_work_order_Agent/main/thumbnail.jpg)


项目安装依赖：
下载好本项目后，在项目文件夹下运行命令：
conda env create -f environment.yml

在本项目文件夹根目录下，创建一个.env文件，用于存放环境变量，目前需要以下变量：
- OPENAI_BASE_URL  模型调用地址，第三方网站需要填（如阿里百炼平台）
- OPENAI_API_KEY   模型密钥
- FEISHU_APP_ID    飞书ID
- FEISHU_APP_SECRET 飞书密钥

在飞书官网，创建自定义机器人，开放权限：

- 获取群组信息
- 获取与发送单聊、群组消息
- 接收群聊中@机器人消息事件

最后，在一个测试群聊里添加这个自定义的机器人。

技能配置(Skill)：
默认技能有打印机故障、网络问题、操作系统异常、账号权限，放在skills文件夹下，如果想添加，按照相同的格式添加。

知识库：
在chroma_db文件夹下有默认的一些技能的示例文档，如果想添改新的文档或为新的技能添加文档，要在knowledge_base.py里进行修改。
修改完成后，运行前将已有的chroma_db文件夹删掉，防止缓存影响运行结果。


启动方法（确定以上配置不再变动后再启动）：

启动fastapi后端，使用本地端口(8000)快速测试：
uvicorn feishu_bot:app --host 127.0.0.1 --port 8000

启动飞书机器人后端：
python feishu_bot_ws.py

之后就可以@机器人进行对话，获取工单卡片。

项目可改动点：

-  使用fastapi部署在服务器上，不仅是本地环路
-  knowledge_base.py 和 retrieval_tools.py 改动，可以和PostgreSQL等工作常用数据库连接
-  运行效率，返回格式等等.......
