"""AI 智能助手核心工具：LLMClient 封装 + 意图路由 + DB 查询 + SSE 流式。

硅基流动（SiliconFlow）大模型调用封装。API_KEY / BASE_URL / MODEL 一律从环境变量读取，禁止硬编码。
任何异常都吞掉并返回友好提示。

硅基流动开放平台（免费额度）：
  BASE_URL = https://api.siliconflow.cn/v1
  免费模型示例：
    Qwen/Qwen2.5-7B-Instruct
    Qwen/Qwen2.5-32B-Instruct
    deepseek-ai/DeepSeek-V3
  注册后在 https://cloud.siliconflow.cn/account/ak 拿 API Key

设置环境变量（任选其一）：
  方式1：PyCharm Run Configuration -> Environment variables
         SILICONFLOW_API_KEY=sk-xxx
  方式2：系统环境变量
         set SILICONFLOW_API_KEY=sk-xxx
  方式3：项目根目录新建 .env（需 pip install python-dotenv）
"""

import json
import os
import re
import time
from datetime import date

try:
    from urllib import request as urlrequest
    from urllib.error import URLError, HTTPError
except ImportError:  # pragma: no cover
    urlrequest = None
    URLError = HTTPError = Exception

try:
    from dotenv import load_dotenv
    from pathlib import Path
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=str(_env_path), override=True)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# 环境变量读取
# ---------------------------------------------------------------------------

def _read_env(name, default=""):
    val = os.environ.get(name, default)
    return val.strip() if isinstance(val, str) else val


def _get_api_key():
    return _read_env("SILICONFLOW_API_KEY", "")


def _get_base_url():
    return _read_env("SILICONFLOW_BASE_URL",
                     "https://api.siliconflow.cn/v1").rstrip("/")


def _get_model():
    return _read_env("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")


# ---------------------------------------------------------------------------
# LLMClient：统一封装（T1）
# ---------------------------------------------------------------------------

class LLMClient:
    """硅基流动兼容客户端，OpenAI 接口协议。"""

    TIMEOUT = 30
    MAX_RETRIES = 2
    TEMPERATURE = 0.7

    @classmethod
    def is_configured(cls):
        return bool(_get_api_key())

    @classmethod
    def chat(cls, prompt, system="", temperature=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return cls._call(messages, temperature=temperature)

    @classmethod
    def chat_history(cls, history, temperature=None):
        return cls._call(history, temperature=temperature)

    @classmethod
    def _call(cls, messages, temperature=None):
        api_key = _get_api_key()
        if not api_key:
            return ("⚠️ 尚未配置硅基流动 API Key。\n"
                    "请在 .env 文件里设置 SILICONFLOW_API_KEY 后再试。\n"
                    "注册入口：https://cloud.siliconflow.cn/account/ak")

        model = _get_model()
        base_url = _get_base_url()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None
                           else cls.TEMPERATURE,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        last_err = None
        for attempt in range(cls.MAX_RETRIES + 1):
            try:
                with urlrequest.urlopen(req, timeout=cls.TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
            except KeyError as e:
                return f"⚠️ 模型返回格式异常（缺少 {e}），请稍后再试。"
            except (URLError, HTTPError) as e:
                last_err = e
            except Exception as e:
                last_err = e
            if attempt < cls.MAX_RETRIES:
                time.sleep(1 + attempt)

        return f"⚠️ 调用硅基流动失败：{last_err}。请检查网络或 API Key。"

    @classmethod
    def chat_stream(cls, messages, temperature=None):
        """SSE 流式输出：逐 chunk yield 文本。无 API Key 或非流式兼容时退化为 _call 一次返回。"""
        api_key = _get_api_key()
        if not api_key:
            yield ("⚠️ 尚未配置硅基流动 API Key，请在 .env 文件里设置 "
                   "SILICONFLOW_API_KEY 后再试。")
            return

        model = _get_model()
        base_url = _get_base_url()
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature if temperature is not None
                           else cls.TEMPERATURE,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=cls.TIMEOUT * 2) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    line = line[5:].strip()
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            yield f"\n⚠️ 流式调用失败：{e}（降级返回完整结果）\n"
            yield cls._call(messages, temperature=temperature)


# ---------------------------------------------------------------------------
# 全局常量
# ---------------------------------------------------------------------------

MAX_INPUT_LEN = 500
MAX_HISTORY_TURNS = 8  # 多轮对话最多保留 8 轮（16 条 messages）
INJECTION_PATTERNS = [
    r"忽略(之前的|上面的|所有)?指令",
    r"假装你是",
    r"system\s*prompt",
    r"你不再是",
    r"disregard",
    r"ignore previous",
]


def sanitize_input(text):
    """过滤用户输入：长度截断 + 注入词检测；返回 (cleaned, warning)。"""
    text = (text or "").strip()
    warning = ""
    if len(text) > MAX_INPUT_LEN:
        text = text[:MAX_INPUT_LEN]
        warning = f"输入过长，已截断为前 {MAX_INPUT_LEN} 字。"
    lower = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, lower):
            warning = ("检测到可疑指令，已做过滤；如需帮助请正常提问。")
            break
    return text, warning


# ---------------------------------------------------------------------------
# 意图识别 + DB 查询工具（T5 数据增强）
# ---------------------------------------------------------------------------

# 寒暄/闲聊词 —— 命中直接走 chat 对话，不查 DB/KB
CHAT_GREETINGS = [
    "你好", "您好", "hi", "hello", "嗨", "哈喽",
    "谢谢", "多谢", "感谢", "再见", "拜拜", "bye",
    "早上好", "中午好", "下午好", "晚上好", "晚安",
    "在吗", "在不在", "忙吗", "干嘛呢",
    "天气", "时间", "几点", "几号", "星期几",
    "笑话", "逗我", "无聊", "聊天",
]

# 业务关键词 → 对应意图
DATA_KEYWORDS = {
    "attendance": ["考勤", "打卡", "出勤", "缺勤", "迟到", "早退"],
    "salary": ["薪资", "工资", "薪水", "奖金", "扣款", "月薪", "实发"],
    "employee": ["员工档案", "员工信息", "员工资料", "在职员工",
                 "是谁", "是哪位", "哪一位", "哪位", "这个人", "手机号", "电话", "工号"],
    "department": ["部门", "科室", "多少人", "几个人", "有哪些人", "多少员工", "员工总数"],
    "knowledge": ["制度", "规定", "政策", "流程", "规则", "怎么请", "怎么报销",
                  "年终奖", "年假", "请假", "报销", "入职", "离职"],
}

# 禁止当人名的前缀（代词/助词）
NAME_BLACKLIST_PREFIX = ("我", "你", "他", "她", "它", "我们", "你们", "他们",
                         "这", "那", "哪", "什么", "怎么", "为什", "如何",
                         "请", "帮", "给", "让", "把")

# 纯问候语（整句只有问候，不含业务内容）—— 视为「新对话开始」，丢弃旧历史
_PURE_GREETING_RE = re.compile(
    r"^\s*(你好|您好|hi|hello|嗨|哈喽|早上好|中午好|下午好|晚上好|"
    r"在吗|在不在|有人吗|哈喽啊)\s*[呀啊哦哈呢]*\s*[!！。.~～?？]*\s*$",
    re.IGNORECASE,
)


def is_pure_greeting(question):
    """整句只有问候语（如「你好」）时返回 True。"""
    return bool(_PURE_GREETING_RE.match(question or ""))


def detect_intent(question):
    """
    识别意图，返回 (intent, matched_keywords)。

    intent 取值：
      'chat'       —— 寒暄/闲聊，走纯 LLM 对话，不查 DB/KB
      'attendance' —— 考勤查询
      'salary'     —— 薪资查询
      'employee'   —— 员工档案查询
      'department' —— 部门查询
      'knowledge'  —— 制度/流程问答（知识库优先）
    """
    q = question.strip()

    # 0. 手机号 / 工号查询 —— 一定是查员工本人
    if re.search(r"1[3-9]\d{9}", q):
        return "employee", ["手机号"]

    # 1. 业务关键词优先（避免「时间」这类词把业务问题误判为闲聊）
    hits = {}
    for intent, kws in DATA_KEYWORDS.items():
        found = [kw for kw in kws if kw in q]
        if found:
            hits[intent] = found

    # 考勤/薪资 优先级最高
    for prio in ["attendance", "salary"]:
        if prio in hits:
            return prio, hits[prio]

    # 制度关键词次之
    if "knowledge" in hits:
        return "knowledge", hits["knowledge"]

    # 员工档案关键词
    if "employee" in hits:
        return "employee", hits["employee"]

    # 2. 句子里直接出现员工姓名（如「行行行是谁」）→ 员工查询
    matched_name = _find_employee_name(q)
    if matched_name:
        return "employee", [matched_name]

    # 3. 句子里出现部门名称（如「技术部有哪些人」）→ 部门查询
    matched_dept = _find_department_title(q)
    if matched_dept:
        return "department", [matched_dept]

    if "department" in hits:
        return "department", hits["department"]

    # 4. 没有任何业务关键词，才判寒暄/闲聊
    q_lower = q.lower()
    for greet in CHAT_GREETINGS:
        if greet in q_lower:
            return "chat", [greet]

    return "chat", []


def _find_department_title(question):
    """在问句中找数据库里真实存在的部门名称，返回部门名或 None。"""
    if len(question) > 30:
        return None
    try:
        from app01.models import Department
        titles = [t for t in Department.objects.values_list("title", flat=True) if t]
    except Exception:
        return None
    for title in sorted(set(titles), key=len, reverse=True):
        if title in question:
            return title
    return None


def _find_employee_name(question):
    """在问句中找数据库里真实存在的员工姓名（长名优先），返回姓名或 None。"""
    if len(question) > 30:
        return None
    try:
        from app01.models import Employee
        names = [n for n in Employee.objects.values_list("name", flat=True) if n]
    except Exception:
        return None
    for name in sorted(set(names), key=len, reverse=True):
        if name in question:
            return name
    return None


# 问句开头的客套/动词，提取人名前先剥掉
_LEAD_VERB_RE = re.compile(
    r"^(?:我想知道|我想查一下|我想查|我想看看|我想看|我想问一下|我想问|"
    r"帮我查一下|帮我查|帮我看看|帮我|麻烦查一下|麻烦|"
    r"查一下|查询一下|查查|看一下|看看|请问一下|请问|"
    r"想问一下|想问|了解一下|想知道|我要查|我要看)\s*"
)

_TAIL_PARTICLE_RE = re.compile(r"(?:的|啊|呀|呢|了|一下|来|情况|记录|详情|信息)$")

# 指代词：出现时说明用户在指上一轮提到的员工，而不是在说一个新名字
_PRONOUN_RE = re.compile(r"(他|她|该员工|这位|这个人|此人|其)")


def extract_name_for_intent(question, intent):
    """
    只在 intent 为 attendance/salary/employee 时才尝试提取人名。
    策略：在意图关键词**前面**找 2-3 个连续汉字作为候选名字。
    指代词（他/她/该员工…）出现时不猜名字，交给历史上下文去解析。
    """
    if intent not in ("attendance", "salary", "employee"):
        return None

    for kw in DATA_KEYWORDS.get(intent, []):
        idx = question.find(kw)
        if idx > 0:
            # 先剥掉「我想知道/帮我查一下」这类开头
            prefix = _LEAD_VERB_RE.sub("", question[:idx]).strip()
            # 指代词 → 不猜名字（如「他具体的入职时间和薪资呢」）
            if _PRONOUN_RE.search(prefix):
                return None
            # 反复去掉结尾的助词/名词（的、情况、记录…）
            for _ in range(3):
                new_prefix = _TAIL_PARTICLE_RE.sub("", prefix).strip()
                if new_prefix == prefix:
                    break
                prefix = new_prefix
            # 取末尾 2-3 个连续汉字
            m = re.search(r"([\u4e00-\u9fff]{2,3})$", prefix)
            if m:
                candidate = m.group(1)
                # 过滤代词开头的非法名字
                if not candidate.startswith(NAME_BLACKLIST_PREFIX):
                    return candidate
    return None


def match_employee_in_question(question, user=None):
    """用数据库里真实的员工姓名去匹配问句，命中返回 Employee，否则 None。

    比正则猜名字可靠得多：'我想知道张伟的考勤情况' 里含有 '张伟' 就能直接命中。
    """
    from app01.models import Employee
    from app01.views.common import scoped_employees

    qs = (scoped_employees(user) if user and user.is_authenticated
          else Employee.objects.all())
    names = [n for n in qs.values_list("name", flat=True) if n]
    for name in sorted(set(names), key=len, reverse=True):
        if name in question:
            return qs.filter(name=name).first()
    return None


def resolve_employee_from_history(history, user=None):
    """从多轮对话历史里找最近提到的员工（手机号优先，其次姓名）。

    用于「他/她的薪资呢」这类指代追问。
    """
    if not history:
        return None
    from app01.models import Employee
    from app01.views.common import scoped_employees

    qs = (scoped_employees(user) if user and user.is_authenticated
          else Employee.objects.all())
    names = sorted(set(n for n in qs.values_list("name", flat=True) if n),
                   key=len, reverse=True)

    # 只看最近 6 条消息，从新到旧
    for msg in reversed(history[-6:]):
        content = msg.get("content") if isinstance(msg, dict) else None
        if not content:
            continue
        phone_m = re.search(r"1[3-9]\d{9}", content)
        if phone_m:
            emp = qs.filter(phone=phone_m.group(0)).first()
            if emp:
                return emp
        for name in names:
            if name in content:
                return qs.filter(name=name).first()
    return None


def lookup_employee_by_name(name, user=None):
    """按姓名查员工，考虑数据范围。"""
    from app01.models import Employee
    from app01.views.common import scoped_employees
    qs = scoped_employees(user) if user and user.is_authenticated \
        else Employee.objects.all()
    return list(qs.filter(name=name.strip()))


def build_context_from_db(question, user=None, intent=None, history=None):
    """
    查 DB 并把真实数据拼进 prompt。
    只在 intent 为 attendance/salary/employee/department 时才查。
    intent=chat/knowledge 直接返回 None。
    history 用于解析「他/她的薪资呢」这类指代追问。
    """
    from app01.models import Employee, Attendance, Salary, Department

    if intent is None:
        intent, _ = detect_intent(question)

    # chat / knowledge 不查 DB
    if intent in ("chat", "knowledge"):
        return None

    parts = []
    employee = None
    candidate = None

    # 1. 员工档案：手机号精确查 > 数据库真名匹配 > 正则兜底
    if intent in ("attendance", "salary", "employee"):
        from app01.views.common import scoped_employees

        qs = (scoped_employees(user) if user and user.is_authenticated
              else Employee.objects.all())

        # 1.1 手机号查询（如「18280076943 是谁」）
        phone_m = re.search(r"1[3-9]\d{9}", question)
        if phone_m:
            emp = qs.filter(phone=phone_m.group(0)).first()
            if emp:
                employee = emp
            else:
                parts.append(
                    f"说明：系统中没有登记手机号为 {phone_m.group(0)} 的员工"
                    f"（或当前账号无权查看该员工）。请如实告知用户。"
                )

        # 1.2 用数据库真名匹配问句
        if employee is None and not phone_m:
            employee = match_employee_in_question(question, user)

        if employee is None and not phone_m:
            candidate = extract_name_for_intent(question, intent)
            if candidate:
                # 候选词里若含有真名（如误切出「道张伟」），纠正回真名
                for real_name in sorted(qs.values_list("name", flat=True),
                                        key=len, reverse=True):
                    if real_name and real_name in candidate:
                        employee = qs.filter(name=real_name).first()
                        candidate = None
                        break

        # 1.3 指代追问：「他/她的薪资呢」→ 从上一轮对话里找提到的员工
        if employee is None and not phone_m and not candidate:
            employee = resolve_employee_from_history(history, user)

        if employee is not None:
            parts.append(
                f"员工档案：姓名={employee.name}，性别={employee.get_gender_display()}，"
                f"年龄={employee.age}，部门={employee.depart.title}，"
                f"手机号={employee.phone}，入职={employee.hire_date}"
            )
        elif candidate:
            parts.append(
                f"说明：系统中查无「{candidate}」这名员工（或当前账号无权查看）。"
                f"请如实告知用户，并提示他可以直接问「我的考勤」「我的薪资」查看本人数据。"
            )
        elif user and user.is_authenticated and not phone_m:
            # 没提名字也没提手机号 → 默认查当前登录员工
            try:
                employee = Employee.objects.get(user=user)
                parts.append(
                    f"当前登录员工：{employee.name}（{employee.depart.title}），"
                    f"以下数据均为该员工本人数据。"
                )
            except Employee.DoesNotExist:
                parts.append("当前账号未关联员工档案，无法查询个人考勤/薪资。")

    # 2. 考勤数据
    if intent == "attendance" and employee:
        recent = Attendance.objects.filter(employee=employee).order_by("-date")[:30]
        if recent:
            lines = [f"{a.date} {a.get_status_display()}"
                     f"（上班 {a.clock_in or '--'}，下班 {a.clock_out or '--'}）"
                     for a in recent]
            parts.append(f"考勤记录（最近 30 条）：" + "；".join(lines))
            normal = sum(1 for a in recent if a.status == "normal")
            late = sum(1 for a in recent if a.status == "late")
            early = sum(1 for a in recent if a.status == "early")
            absent = sum(1 for a in recent if a.status == "absent")
            parts.append(
                f"统计（最近 30 条考勤）：按时 {normal} 次，迟到 {late} 次，"
                f"早退 {early} 次，缺勤 {absent} 次。"
            )
        else:
            parts.append("该员工暂无考勤记录。")

    # 3. 薪资数据
    if intent == "salary" and employee:
        recent = Salary.objects.filter(employee=employee).order_by("-month")[:6]
        if recent:
            lines = [
                f"{s.month} 基本={s.base_salary} 奖金={s.bonus} "
                f"扣款={s.deduction} 实发={s.total}"
                for s in recent
            ]
            parts.append(f"薪资记录（最近 6 个月）：" + "；".join(lines))
        else:
            parts.append("该员工暂无薪资记录。")

    # 4. 部门
    if intent == "department":
        from app01.views.common import scoped_employees

        title = _find_department_title(question)
        if title:
            dept = Department.objects.filter(title=title).first()
            emps = (scoped_employees(user) if user and user.is_authenticated
                    else Employee.objects.all()).filter(depart=dept)
            names = "、".join(f"{e.name}（{e.age}岁，{e.get_gender_display()}）"
                             for e in emps)
            parts.append(f"{title}共 {emps.count()} 人：{names or '暂无员工'}")
        else:
            lines = []
            for d in Department.objects.all():
                cnt = Employee.objects.filter(depart=d).count()
                lines.append(f"{d.title}({cnt}人)")
            total = Employee.objects.count()
            parts.append(f"公司共 {Department.objects.count()} 个部门、{total} 名员工。"
                         + "部门分布：" + "；".join(lines))

    return "\n".join(parts) if parts else None


# ---------------------------------------------------------------------------
# 制度知识库检索（T3）
# ---------------------------------------------------------------------------

def retrieve_knowledge(question):
    """按关键词在 Knowledge 表检索；返回命中条目文本，没命中返回 None。"""
    from app01.models import Knowledge
    if not Knowledge.objects.exists():
        return None

    q = question.strip()

    # 候选词 = 基础三字段匹配 + 标点拆分 + n-gram 滑动窗口
    keyword_matches = (
        Knowledge.objects.filter(keywords__icontains=q)
        | Knowledge.objects.filter(title__icontains=q)
        | Knowledge.objects.filter(content__icontains=q)
    )

    # 1. 按标点拆分（处理 "考勤、请假、薪资" 这种）
    tokens = [t for t in re.split(r"[\s，,。.、/\\!?！？]+", q) if len(t) >= 2]

    # 2. n-gram 滑动窗口（2~4 字），处理 "请假怎么请" 这种无标点的自然问句
    for n in (2, 3):
        for i in range(len(q) - n + 1):
            piece = q[i:i + n]
            if re.match(r'^[\u4e00-\u9fff]+$', piece):
                tokens.append(piece)

    # 去重，按长度降序（越长越精准，先匹配）
    seen = set()
    uniq_tokens = []
    for t in sorted(tokens, key=len, reverse=True):
        if t not in seen:
            seen.add(t)
            uniq_tokens.append(t)

    for tok in uniq_tokens:
        keyword_matches = (
            keyword_matches
            | Knowledge.objects.filter(keywords__icontains=tok)
            | Knowledge.objects.filter(content__icontains=tok)
            | Knowledge.objects.filter(title__icontains=tok)
        )

    keyword_matches = keyword_matches.distinct()[:5]
    if not keyword_matches:
        return None
    return "\n\n".join(
        f"[{k.category}] {k.title}：{k.content}" for k in keyword_matches
    )


# ---------------------------------------------------------------------------
# JD 生成三段式提示词（T2）
# ---------------------------------------------------------------------------

JD_SYSTEM = (
    "你是一名资深 HR 招聘专家，擅长撰写结构化、有吸引力的中文招聘 JD。"
    "输出必须严格按三段：岗位职责、任职要求、薪资福利。每段 3-6 条，"
    "用项目符号列出，语言简洁专业。"
)

JD_PROMPT_TEMPLATE = """请为「{job_title}」岗位写一份专业的中文招聘 JD（Job Description）。

要求：
1. 岗位职责：5-8 条，清晰描述该岗位日常工作与核心交付物
2. 任职要求：基本要求（学历/经验）、必备技能、加分项，分 3 小节
3. 薪资福利：给出薪资区间、社保福利、培训发展

输出格式：用 Markdown，三个二级标题 ## 岗位职责 / ## 任职要求 / ## 薪资福利，每段项目符号。岗位：{job_title}"""


def generate_jd(job_title):
    """T2：用三段式提示词生成结构化 JD。"""
    prompt = JD_PROMPT_TEMPLATE.format(job_title=job_title.strip())
    return LLMClient.chat(prompt, system=JD_SYSTEM)


# ---------------------------------------------------------------------------
# 数据智能点评（T4）
# ---------------------------------------------------------------------------

def build_review_context(employee_id, month=None):
    """读取考勤 + 薪资，拼点评上下文。"""
    from app01.models import Employee, Attendance, Salary

    try:
        emp = Employee.objects.get(pk=employee_id)
    except Employee.DoesNotExist:
        return None

    parts = [
        f"员工：{emp.name}（{emp.depart.title}），年龄 {emp.age}，入职 {emp.hire_date}。"
    ]

    # 考勤
    if month:
        attendances = Attendance.objects.filter(
            employee=emp, date__startswith=month
        ).order_by("date")
    else:
        attendances = Attendance.objects.filter(employee=emp).order_by("-date")[:30]

    if attendances:
        status_counts = {}
        for a in attendances:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
        parts.append(
            f"考勤（{month or '最近 30 条'}）："
            f"按时 {status_counts.get('normal', 0)} 次、"
            f"迟到 {status_counts.get('late', 0)} 次、"
            f"早退 {status_counts.get('early', 0)} 次、"
            f"缺勤 {status_counts.get('absent', 0)} 次。"
        )
    else:
        parts.append("该时段暂无考勤记录。")

    # 薪资
    if month:
        try:
            salary = Salary.objects.get(employee=emp, month=month)
            parts.append(
                f"薪资（{month}）：基本 {salary.base_salary}、"
                f"奖金 {salary.bonus}、扣款 {salary.deduction}、实发 {salary.total}。"
            )
        except Salary.DoesNotExist:
            parts.append(f"{month} 暂无薪资记录。")
    else:
        salaries = Salary.objects.filter(employee=emp).order_by("-month")[:3]
        if salaries:
            parts.append(
                "最近薪资：" + "；".join(
                    f"{s.month} 实发 {s.total}" for s in salaries
                )
            )

    return "\n".join(parts)


REVIEW_SYSTEM = (
    "你是一名专业的 HR 数据分析师。基于给定的考勤和薪资数据，"
    "用一句话（80-150 字）给出合理点评，指出亮点和改进建议。"
    "语气客观、专业，不要虚构数据。"
)


def generate_review(employee_id, month=None):
    """T4：输出一句数据点评 + 改进建议。"""
    ctx = build_review_context(employee_id, month)
    if not ctx:
        return "⚠️ 未找到该员工，请确认 ID 是否正确。"
    prompt = (
        f"请基于以下员工数据，给出一句简洁的点评和改进建议：\n\n{ctx}"
    )
    return LLMClient.chat(prompt, system=REVIEW_SYSTEM)


# ---------------------------------------------------------------------------
# 知识 + DB 混合回答（T3 + T5）
# ---------------------------------------------------------------------------

CHAT_SYSTEM = (
    "你是企业员工管理系统的 AI 助手，名叫「小 E」，像同事一样自然聊天。"
    "用户问什么就答什么，不要绕弯子、不要反问工号。"
    "回答可以自然地多聊一两句：补充一点相关知识、建议或追问都行，但别长篇大论，"
    "控制在 200 字以内。如果用户聊的是与系统无关的话题（天气、笑话、闲聊），"
    "正常聊天即可，不必硬拉回 HR 话题。"
)

HYBRID_SYSTEM = (
    "你是企业员工管理系统的 AI 助手。"
    "回答规则：\n"
    "1. 先直接回答用户的问题，结论放第一句，不要反问工号、不要让用户再提供条件；\n"
    "2. 有「真实数据」就基于数据说清楚（姓名、时间、数字都要具体），不要虚构；\n"
    "3. 有「制度条款」就引用条款要点，用一两句话讲明白；\n"
    "4. 回答完再延伸一点有价值的信息，例如相关制度提醒、趋势判断或改进建议，最多两句；\n"
    "5. 数据或制度里确实没有的，直说「这部分系统里没有记录」，不要编造；\n"
    "6. 同一组数字只说一遍，不要反复罗列；统计口径按参考信息里写的说（如「最近 30 条」）。\n"
    "总长度控制在 300 字以内，语气专业又亲切。"
)

KNOWLEDGE_SYSTEM = (
    "你是企业制度问答助手。"
    "先直接回答用户的问题，再引用制度条款中的关键内容；"
    "条款里没有的部分明确说「制度里没有相关规定」。"
    "回答完可以补一句实用提醒（比如申请时限、注意事项），不超过 300 字。"
)


def answer_hybrid(question, user=None, extra_context=None, history=None):
    """
    总入口：根据意图选择策略。
    - chat → 纯 LLM 自由对话
    - knowledge → 查知识库 + LLM 基于制度回答
    - attendance/salary/employee/department → 查 DB + KB → LLM 基于事实回答
    """
    intent, _ = detect_intent(question)

    # 纯问候语 = 新对话开始：不携带任何历史，避免旧话题（如上次问的某员工）串进来
    if is_pure_greeting(question):
        history = None

    system_prompt = ""
    user_prompt = ""

    # 1. 寒暄闲聊 → 纯 LLM，不加任何上下文
    if intent == "chat":
        system_prompt = CHAT_SYSTEM
        user_prompt = question

    # 2. 制度问答 → 先查 KB
    elif intent == "knowledge":
        kb_ctx = retrieve_knowledge(question)
        system_prompt = KNOWLEDGE_SYSTEM
        if kb_ctx:
            user_prompt = (
                f"请基于以下制度条款回答用户问题。"
                f"条款里没有的内容请说「制度里没有相关规定」：\n\n"
                f"【制度条款】\n{kb_ctx}\n\n【用户问题】\n{question}"
            )
        else:
            user_prompt = (
                f"用户问题：{question}\n\n（知识库中没有找到直接相关的制度条款，"
                f"请根据你的理解回答，如果确实不知道就说「抱歉，我不太确定」）"
            )

    # 3. 业务查询 → DB + KB 混合
    else:
        db_ctx = build_context_from_db(question, user, intent=intent, history=history)
        kb_ctx = retrieve_knowledge(question)
        system_prompt = HYBRID_SYSTEM

        parts = [f"用户问题：{question}"]
        if db_ctx:
            parts.append("【真实数据】\n" + db_ctx)
        if kb_ctx:
            parts.append("【公司制度】\n" + kb_ctx)
        if not db_ctx and not kb_ctx:
            parts.append(
                "注意：既没有匹配的员工数据，也没有相关制度条款。"
                "请诚实地回复「我不知道」，不要编造信息。"
            )
        user_prompt = "\n\n".join(parts)

    # --- 调用 LLM：有 history 就拼 messages ---
    if history:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})
        return LLMClient.chat_history(messages)

    # 无 history 的简单调用
    return LLMClient.chat(user_prompt, system=system_prompt)
