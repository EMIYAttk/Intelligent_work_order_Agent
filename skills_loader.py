import yaml
import importlib.util
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
import pathlib

# 获取 skills_loader.py 所在目录的父级（即 project/）
script_dir = pathlib.Path(__file__).parent
skills_dir = script_dir / "skills"   # 绝对路径
def load_skills_from_directory(skills_base_dir: str) -> List[Dict[str, Any]]:
    """
    从指定基础目录加载所有技能（每个技能为子文件夹）。
    每个技能子文件夹需包含 SKILL.md 文件，可选 tools.py。
    返回技能列表，每个技能包含 name, description, tools (List[BaseTool]), content。
    """
    skills = []
    base_path = Path(skills_base_dir)

    if not base_path.exists():
        print(f"⚠️ 技能目录不存在: {skills_base_dir}")
        return skills

    for skill_dir in base_path.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            print(f"⚠️ 跳过 {skill_dir.name}：缺少 SKILL.md")
            continue

        # 读取 SKILL.md
        content = skill_md.read_text(encoding='utf-8')
        name = skill_dir.name  # 默认使用文件夹名
        description = ""
        tools_names = []
        main_content = content.strip()

        # 解析 YAML front matter
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                front_matter = parts[1]
                main_content = parts[2].strip()
                try:
                    meta = yaml.safe_load(front_matter)
                    if meta:
                        name = meta.get('name', name)
                        description = meta.get('description', '')
                        tools_names = meta.get('tools', [])
                except yaml.YAMLError as e:
                    print(f"⚠️ YAML 解析错误 {skill_md}: {e}")

        # 如果没有 description，尝试从主内容中提取第一行
        if not description and main_content:
            description = main_content.split('\n')[0].strip()

        # 加载工具
        tools = []
        tools_py = skill_dir / "tools.py"
        if tools_py.exists():
            # 动态导入 tools.py 模块
            module_name = f"skills_{skill_dir.name}"  # 确保唯一性
            try:
                spec = importlib.util.spec_from_file_location(module_name, tools_py)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # 获取工具对象
                    for tool_name in tools_names:
                        if hasattr(module, tool_name):
                            tool_obj = getattr(module, tool_name)
                            if isinstance(tool_obj, BaseTool):
                                tools.append(tool_obj)
                            else:
                                print(f"⚠️ 工具 {tool_name} 在 {skill_dir.name}/tools.py 中不是 BaseTool 实例，将忽略")
                        else:
                            print(f"⚠️ 技能 {skill_dir.name} 声明的工具 {tool_name} 未在 tools.py 中找到")
                else:
                    print(f"⚠️ 无法加载模块 {tools_py}")
            except Exception as e:
                print(f"⚠️ 导入 {tools_py} 失败: {e}")
        else:
            if tools_names:
                print(f"⚠️ 技能 {skill_dir.name} 声明了工具 {tools_names}，但缺少 tools.py")

        skill = {
            "name": name,
            "description": description,
            "tools": tools,  # List[BaseTool]
            "content": main_content
        }
        skills.append(skill)
        print(f"✅ 已加载技能: {name} (工具数量: {len(tools)})")

    return skills


SKILLS = load_skills_from_directory(skills_dir)
