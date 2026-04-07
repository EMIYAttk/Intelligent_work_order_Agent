# knowledge_base.py
import chromadb
from pathlib import Path
from typing import List, Dict, Tuple
from chromadb.utils import embedding_functions

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-zh-v1.5"  # 中文专用
)
class KnowledgeBaseManager:
    """ChromaDB 知识库管理 - 负责初始化、保存示例文档"""
    
    def __init__(self, db_path: str = "./chroma_db"):
        self.db_path = db_path
        # 使用新的 PersistentClient 进行本地持久化
        self.client = chromadb.PersistentClient(path=db_path)
        
    def init_all_collections(self):
        """初始化所有技能的知识库（每个技能一个Collection）"""
        # 4个典型故障类型的示例文档
        skill_docs = {
            "hardware_printer": [
                {
                    "id": "printer_jam",
                    "content": "【打印机卡纸处理】第一步：立即停止使用，关闭打印机电源。第二步：打开后盖（激光）或前盖（喷墨），缓慢取出卡纸，检查碎纸残留。第三步：检查纸张是否潮湿或超载（不超过纸盒80%）。第四步：重新装纸测试。如频繁卡纸，可能是搓纸轮老化需更换。",
                    "metadata": {"category": "卡纸", "urgency": "medium"}
                },
                {
                    "id": "printer_offline",
                    "content": "【打印机脱机恢复】USB打印机：更换接口或线缆。网络打印机：确认屏幕显示IP正常。Windows：设置-蓝牙和其他设备-打印机，右键取消勾选'脱机使用'。macOS：系统设置-打印机与扫描仪，点击'恢复'。网络打印机可浏览器访问IP查看状态。",
                    "metadata": {"category": "连接", "urgency": "low"}
                },
                {
                    "id": "printer_quality",
                    "content": "【打印质量差处理】激光打印机：取出硒鼓摇晃5-6次使碳粉均匀，检查寿命（低于10%更换）。喷墨打印机：执行'打印头清洗'（控制面板-维护），无效则'深度清洗'（注意耗墨）。检查纸张类型设置是否匹配。",
                    "metadata": {"category": "质量", "urgency": "low"}
                }
            ],
            "hardware_network": [
                {
                    "id": "wifi_disconnect",
                    "content": "【WiFi频繁断开】确认是否仅单台设备问题。Windows：设备管理器-网络适配器，右键无线网卡卸载并勾选'删除驱动'，重启自动重装。修改DNS为8.8.8.8和114.114.114.114。检查路由器信道干扰，建议用WiFi分析App选择1/6/11信道。",
                    "metadata": {"category": "WiFi", "urgency": "high"}
                },
                {
                    "id": "cable_issue",
                    "content": "【有线网络排查】观察网口指示灯：绿灯常亮+黄灯闪烁正常，全灭为物理故障。更换网线测试。检查IP设置是否为自动获取（DHCP）。命令提示符执行：ipconfig/release 后 ipconfig/renew。如获取169.254.x.x说明DHCP失败。ping网关测试连通性。",
                    "metadata": {"category": "有线", "urgency": "high"}
                },
                {
                    "id": "network_slow",
                    "content": "【网络速度慢】speedtest.cn测速，低于签约带宽50%则有问题。重启路由器和光猫。检查是否有设备大流量下载。更换DNS。检查网线规格（千兆需Cat5e以上）。企业网络联系网管检查QoS策略。",
                    "metadata": {"category": "速度", "urgency": "medium"}
                }
            ],
            "software_os": [
                {
                    "id": "blue_screen",
                    "content": "【蓝屏紧急处理】记录错误代码（如CRITICAL_PROCESS_DIED）。强制重启后如无法进入系统，强制断电3次触发恢复模式，选择'疑难解答-高级选项-启动设置-启用安全模式'。安全模式下：卸载近期软件、回滚驱动（设备管理器-属性-驱动程序-回退）、运行sfc /scannow修复系统文件。",
                    "metadata": {"category": "蓝屏", "urgency": "urgent"}
                },
                {
                    "id": "slow_boot",
                    "content": "【系统卡顿优化】Ctrl+Shift+Esc打开任务管理器-启动，禁用非必要启动项。磁盘清理：勾选临时文件和系统错误内存转储。CrystalDiskInfo检查硬盘健康。SSD确保AHCI模式开启。虚拟内存设为物理内存1.5-2倍固定大小。机械硬盘建议升级SSD。",
                    "metadata": {"category": "卡顿", "urgency": "low"}
                },
                {
                    "id": "update_fail",
                    "content": "【更新失败处理】错误0x80070002：删除C:\\Windows\\SoftwareDistribution\\Download内文件后重试。错误0x80240034：运行Windows更新疑难解答。手动安装：访问Microsoft Update Catalog搜索KB号下载。macOS：检查35GB以上空间，重置NVRAM（开机Option+Command+P+R 20秒）。",
                    "metadata": {"category": "更新", "urgency": "medium"}
                }
            ],
            "software_account": [
                {
                    "id": "account_locked",
                    "content": "【账号解锁流程】常见原因：连续5次输错密码、长期未登录（90天+）、异地登录触发安全。验证身份（工号、部门、主管）。AD控制台查看锁定原因。执行解锁（Unlock-ADAccount）。强制下次登录修改密码。异地登录需确认是否本人出差，必要时启用MFA。发送邮件告知安全规范。",
                    "metadata": {"category": "锁定", "urgency": "high"}
                },
                {
                    "id": "password_reset",
                    "content": "【密码重置SOP】身份验证：必须面对面验证工牌或企业微信视频，禁止仅凭电话。ADUC右键账户-重置密码，设置临时密码（如Pass1234!），勾选'下次登录须更改'。告知用户临时密码（短信/企微，禁止邮件）。指导设置12位以上强密码（大小写+数字+特殊字符）。记录重置日志。",
                    "metadata": {"category": "密码", "urgency": "medium"}
                },
                {
                    "id": "permission_apply",
                    "content": "【权限申请处理】用户提交OA工单并经部门经理审批。共享文件夹：右键-属性-安全-高级-添加用户组。软件管理员权限：建议'以管理员身份运行'而非直接加入Admin组。VPN权限：防火墙/VPN网关添加至对应用户组。定期审计权限（每季度）。禁止直接开通域管理员权限，特殊情况需CTO签字。",
                    "metadata": {"category": "权限", "urgency": "low"}
                }
            ]
        }
        
        for collection_name, docs in skill_docs.items():
            self._create_or_update_collection(collection_name, docs)
            
        print(f"✅ 已初始化 {len(skill_docs)} 个知识库")
    
    def _create_or_update_collection(self, collection_name: str, docs: List[Dict]):
        """创建或更新Collection"""
        try:
            # 尝试获取已有collection
            collection = self.client.get_collection(collection_name,embedding_function=embedding_fn)
            print(f"   Collection '{collection_name}' 已存在，跳过")
        except:
            # 创建新collection
            collection = self.client.create_collection(name=collection_name,embedding_function=embedding_fn)
            
            if docs:
                collection.add(
                    documents=[d["content"] for d in docs],
                    ids=[d["id"] for d in docs],
                    metadatas=[d["metadata"] for d in docs]
                )
                # 新版本自动持久化，无需显式调用 persist()
                print(f"   ✅ 创建 '{collection_name}' 并插入 {len(docs)} 个文档")
    
    def get_collection(self, skill_id: str):
        """获取指定skill的collection（供检索工具使用）"""
        collection_name = f"skill_{skill_id}"
        try:
            return self.client.get_collection(collection_name)
        except:
            return None

# 初始化代码（首次运行执行）
if __name__ == "__main__":
    kb = KnowledgeBaseManager()
    kb.init_all_collections()