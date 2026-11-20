"""任务管理视图：AJAX 异步提交，后端返回 JSON，前端回显校验错误。（对应任务书 T9 AJAX 任务）

本文件有三个视图：
- task_list：渲染任务列表页，并把空白 TaskForm 一起交给模板；
- task_create_ajax：接收前端 AJAX 提交，校验通过后创建任务，返回 JSON（含新任务行 HTML）；
- task_delete：任务行右侧「删除」按钮提交后删除该任务并回到列表。
"""

# 讲解要点（结合浏览器里看到的页面效果）：
# 1. 在任务页填好内容点「保存任务」，页面完全没有跳转、地址栏不变，任务表格里立刻多出一行——
#    对应 task_create_ajax 成功后返回 {'ok': True, 'html': 渲染好的 _task_row.html}，
#    前端 $.ajax 的 success 回调把这段 HTML 插到表格里。
# 2. 标题留空直接点提交，页面停在原地，标题输入框下方出现红色错误文字——
#    对应表单不合法时返回 HTTP 400 和 errors 字典（{字段: [提示]}），前端逐字段把红字显示出来。
# 3. 按 F12 打开「网络」面板再提交，能看到 task_create_ajax 的请求方法是 POST，
#    请求头里带 X-CSRFToken——对应 Django 的 CSRF 防护（模板里的 csrf_token 由 JS 塞进请求头）。
# 4. 任务表格每行都能直接显示负责人和其部门，加载不卡顿——
#    对应 task_list 中的 select_related('owner', 'owner__depart') 关联查询优化。

import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from app01.forms import TaskForm
from app01.middleware.permission import require_perm
from app01.models import Task

logger = logging.getLogger('app01')


@require_perm('task:view')
def task_list(request):
    tasks = Task.objects.select_related('owner', 'owner__depart')
    return render(
        request,
        'app01/task_list.html',
        {'tasks': tasks, 'form': TaskForm()},
    )


@require_perm('task:add')
def task_create_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'errors': {'__all__': ['仅支持 POST 请求']}}, status=405)

    form = TaskForm(request.POST)
    if not form.is_valid():
        errors = {
            field: [str(message) for message in field_errors]
            for field, field_errors in form.errors.items()
        }
        logger.info('任务 AJAX 校验失败：%s', errors)
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    task = form.save()
    html = render_to_string(
        'app01/_task_row.html', {'task': task}, request=request
    )
    logger.info('任务 AJAX 创建成功：id=%s', task.id)
    return JsonResponse(
        {
            'ok': True,
            'id': task.id,
            'message': '任务创建成功',
            'html': html,
        }
    )


@require_perm('task:delete')
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    title = task.title
    task.delete()
    messages.success(request, f'任务「{title}」已删除')
    return redirect('task_list')
