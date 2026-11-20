"""AI 智能助手视图：悬浮球聊天（SSE 流式）+ JD 生成 + 制度问答 + 数据点评。

任务书 T2~T7 实现：
  T1  LLMClient 封装 → utils/ai.py
  T2  JD 生成 → jd_generate
  T3  制度知识库问答 → knowledge_ask
  T4  数据智能点评 → employee_review
  T5  多轮对话 + DB 数据增强 → ai_chat_floating（意图路由）
  T6  安全过滤 → utils/ai.sanitize_input
  T7  SSE 流式输出 → ai_chat_sse
"""
import json

from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import date

from app01.utils.ai import (
    LLMClient, MAX_HISTORY_TURNS,
    sanitize_input, answer_hybrid, generate_jd, generate_review,
    is_pure_greeting,
)


# ---------------------------------------------------------------
# T5 + T6  悬浮球聊天（多轮 + 输入过滤 + 意图路由）
# ---------------------------------------------------------------
@csrf_exempt
def ai_chat_floating(request):
    """悬浮球聊天接口：多轮对话，历史存 session，输入过滤，DB + 知识库增强。"""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "请用 POST 请求"},
                            json_dumps_params={"ensure_ascii": False})

    question_raw = (request.POST.get("question") or "").strip()
    reset = request.POST.get("reset") == "1"

    if reset:
        request.session.pop("ai_floating_history", None)
        request.session.modified = True
        return JsonResponse({"ok": True, "result": "对话已清空"},
                            json_dumps_params={"ensure_ascii": False})

    question, warning = sanitize_input(question_raw)
    if not question:
        return JsonResponse({"ok": False, "error": "请输入问题"},
                            json_dumps_params={"ensure_ascii": False})

    # 多轮：把 history 传给 answer_hybrid，让 LLM 有上下文
    history = request.session.get("ai_floating_history", [])

    # 纯问候语视为开启新对话：丢弃旧历史，避免上次聊过的员工/话题串进来
    if is_pure_greeting(question):
        history = []

    # answer_hybrid 内部会根据意图选策略（chat/knowledge/业务），并拼 history
    enhanced = answer_hybrid(question, user=request.user, history=history)

    # 保存历史（用户问题 + 最终回答）
    answer_text = enhanced
    if warning:
        answer_text = f"（{warning}）{answer_text}"

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer_text})
    if len(history) > MAX_HISTORY_TURNS * 2:
        history = history[-(MAX_HISTORY_TURNS * 2):]
    request.session["ai_floating_history"] = history
    request.session.modified = True

    return JsonResponse({"ok": True, "result": answer_text},
                        json_dumps_params={"ensure_ascii": False})


# ---------------------------------------------------------------
# T5  悬浮球历史记录（切换页面后回填气泡）
# ---------------------------------------------------------------
def ai_chat_history(request):
    """返回 session 中保存的悬浮球对话历史，供页面加载时恢复气泡内容。"""
    history = request.session.get("ai_floating_history", []) or []
    return JsonResponse(
        {"ok": True, "messages": history},
        json_dumps_params={"ensure_ascii": False},
    )


# ---------------------------------------------------------------
# T7  SSE 流式输出
# ---------------------------------------------------------------
@csrf_exempt
def ai_chat_sse(request):
    """流式聊天接口：SSE 协议，逐 chunk 推送。前端用 EventSource/fetch 消费。"""
    if request.method != "POST":
        return HttpResponse("请用 POST", status=405)

    question_raw = (request.POST.get("question") or "").strip()
    question, warning = sanitize_input(question_raw)
    if not question:
        return HttpResponse("请输入问题", status=400)

    history = request.session.get("ai_floating_history", [])

    # 纯问候语视为开启新对话：丢弃旧历史，避免上次聊过的员工/话题串进来
    if is_pure_greeting(question):
        history = []

    # 根据意图选 system prompt
    from app01.utils.ai import (
        detect_intent, build_context_from_db, retrieve_knowledge,
        CHAT_SYSTEM, HYBRID_SYSTEM, KNOWLEDGE_SYSTEM,
    )
    intent, _ = detect_intent(question)

    if intent == "chat":
        system_content = CHAT_SYSTEM
    else:
        system_content = HYBRID_SYSTEM if intent != "knowledge" else KNOWLEDGE_SYSTEM
        # 业务查询：拼 DB + KB 上下文
        db_ctx = build_context_from_db(
            question, user=request.user, intent=intent, history=history,
        )
        kb_ctx = retrieve_knowledge(question)
        extra_parts = []
        if db_ctx:
            extra_parts.append("【真实数据】\n" + db_ctx)
        if kb_ctx:
            extra_parts.append("【公司制度】\n" + kb_ctx)
        if extra_parts:
            system_content += "\n\n以下是本次问题的参考信息，优先基于这些回答，不要虚构：\n\n"
            system_content += "\n\n".join(extra_parts)
        else:
            system_content += (
                "\n\n（本次问题既没有匹配的员工数据，也没有相关制度条款，"
                "请根据你的理解回答，如果确实不知道就说不知道）"
            )

    messages = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    final_answer = []

    def gen():
        try:
            for chunk in LLMClient.chat_stream(messages):
                final_answer.append(chunk)
                # SSE 格式：每个事件块以 data: 开头，用 \n\n 分隔
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except GeneratorExit:
            # 客户端断连 —— 仍然需要保存 history（放 finally）
            pass
        except Exception as e:
            yield f"data: {json.dumps({'content': f'\\n⚠️ 服务异常：{e}'}, ensure_ascii=False)}\n\n"
        finally:
            # 无论正常结束、异常还是客户端断连，都保存 history。
            # 注意：流式响应时中间件早已执行完 process_response，
            # 必须显式 session.save() 才会真正落库，否则多轮对话上下文会丢失。
            if final_answer:
                saved_history = list(history)
                saved_history.append({"role": "user", "content": question})
                full = "".join(final_answer)
                if warning:
                    full = f"（{warning}）{full}"
                saved_history.append({"role": "assistant", "content": full})
                if len(saved_history) > MAX_HISTORY_TURNS * 2:
                    saved_history = saved_history[-(MAX_HISTORY_TURNS * 2):]
                try:
                    request.session["ai_floating_history"] = saved_history
                    request.session.modified = True
                    request.session.save()
                except Exception:
                    pass

    return StreamingHttpResponse(
        gen(),
        content_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------
# T2  JD 生成
# ---------------------------------------------------------------
@csrf_exempt
@require_http_methods(["POST"])
def jd_generate(request):
    """T2：输入岗位名 → 生成结构化招聘 JD。"""
    from app01.utils.ai import generate_jd

    job_title_raw = (request.POST.get("job_title") or "").strip()
    job_title, warning = sanitize_input(job_title_raw)

    if not job_title:
        return JsonResponse({"ok": False, "error": "请输入岗位名称"},
                            json_dumps_params={"ensure_ascii": False})
    if len(job_title) < 2:
        return JsonResponse({"ok": False, "error": "岗位名称至少 2 个字符"},
                            json_dumps_params={"ensure_ascii": False})

    result = generate_jd(job_title)
    if result.startswith("⚠️"):
        return JsonResponse({"ok": False, "error": result},
                            json_dumps_params={"ensure_ascii": False})
    if warning:
        result = f"（{warning}）\n\n{result}"
    return JsonResponse({"ok": True, "result": result, "job_title": job_title},
                        json_dumps_params={"ensure_ascii": False})


# ---------------------------------------------------------------
# T3  制度知识库问答
# ---------------------------------------------------------------
@csrf_exempt
def knowledge_ask(request):
    """T3：用户问题 → 关键词检索 Knowledge → 拼进 prompt → LLM 回答；
    资料里没有就老老实实回答「不知道」。"""
    from app01.utils.ai import retrieve_knowledge

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "请用 POST 请求"},
                            json_dumps_params={"ensure_ascii": False})

    question_raw = (request.POST.get("question") or "").strip()
    question, warning = sanitize_input(question_raw)
    if not question:
        return JsonResponse({"ok": False, "error": "请输入问题"},
                            json_dumps_params={"ensure_ascii": False})

    kb_text = retrieve_knowledge(question)
    if not kb_text:
        result = "抱歉，我的知识库里暂时没有相关制度，请咨询 HR 或管理员。"
    else:
        prompt = (
            f"请基于以下制度条款回答用户问题，不要编造，"
            f"回答简洁、不超过 300 字：\n\n"
            f"【制度条款】\n{kb_text}\n\n【用户问题】\n{question}"
        )
        result = LLMClient.chat(prompt, system=(
            "你是企业制度问答助手。只根据给出的制度条款回答，"
            "条款里没有的内容请说「制度里没有相关规定」。"
        ))

    if warning:
        result = f"（{warning}）{result}"
    return JsonResponse({"ok": True, "result": result, "found": bool(kb_text)},
                        json_dumps_params={"ensure_ascii": False})


# ---------------------------------------------------------------
# T4  数据智能点评
# ---------------------------------------------------------------
@csrf_exempt
def employee_review(request):
    """T4：输入员工 ID + 可选月份 → 读考勤薪资 → LLM 输出点评。"""
    from app01.models import Employee
    from app01.utils.ai import generate_review

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "请用 POST 请求"},
                            json_dumps_params={"ensure_ascii": False})

    try:
        employee_id = int(request.POST.get("employee_id") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "员工 ID 不合法"},
                            json_dumps_params={"ensure_ascii": False})

    month = (request.POST.get("month") or "").strip() or None
    # 权限：普通员工只能点评自己
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "请先登录"}, status=401)
    if request.user.is_authenticated and not (
        request.user.is_super_admin or request.user.is_superuser
        or request.user.has_perm_code("employee:view")
    ):
        try:
            my = Employee.objects.get(user=request.user)
            if my.pk != employee_id:
                return JsonResponse({"ok": False, "error": "无权点评其他员工"}, status=403,
                                    json_dumps_params={"ensure_ascii": False})
        except Employee.DoesNotExist:
            return JsonResponse({"ok": False, "error": "无权点评其他员工"}, status=403,
                                json_dumps_params={"ensure_ascii": False})

    if not Employee.objects.filter(pk=employee_id).exists():
        return JsonResponse({"ok": False, "error": "员工不存在"},
                            json_dumps_params={"ensure_ascii": False})

    review = generate_review(employee_id, month=month)
    return JsonResponse({"ok": True, "result": review, "employee_id": employee_id, "month": month},
                        json_dumps_params={"ensure_ascii": False})


# ---------------------------------------------------------------
# T2  JD 生成页面（GET 渲染模板）
# ---------------------------------------------------------------
QUICK_JD_TAGS = ['前端工程师', '后端工程师', 'Java开发', '产品经理',
                 'UI设计师', '测试工程师', '数据分析师', 'HR专员']


def ai_jd_page(request):
    """JD 生成工具页面：输入岗位 → 调用后端生成 → 展示结构化 JD。"""
    return render(request, 'app01/ai_jd.html', {
        'quick_tags': QUICK_JD_TAGS,
        'ai_ready': LLMClient.is_configured(),
    })


# ---------------------------------------------------------------
# T3  制度知识库问答页面（GET 渲染模板）
# ---------------------------------------------------------------
def ai_knowledge_page(request):
    """制度问答页面：输入问题 → 检索 Knowledge → 展示答案。"""
    from app01.models import Knowledge

    samples = list(Knowledge.objects.order_by('category', 'title')
                   .values('id', 'category', 'title')[:12])
    return render(request, 'app01/ai_knowledge.html', {'samples': samples})
