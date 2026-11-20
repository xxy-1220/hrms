"""部门管理视图：新增、查询、编辑、删除。

职责（对应任务书 T2 部门管理，涉及 T5 权限控制、T11 ORM 性能优化）：
部门列表（人数统计 + 搜索 + 分页）、新增、编辑、删除。
所有视图都用 @require_perm('department:xxx') 做接口级权限校验，
模板里再用 {% has_perm_code %} 隐藏无权限按钮，形成“前后端双保险”。

术语：装饰器 = 给视图函数套一层“先检查再执行”的包装；GET 用于看页面，
POST 用于提交修改，删除只接受 POST，避免误触或爬虫触发。
"""

# 讲解要点：
# 1. 页面现象：部门列表每个部门后面显示人数（如“技术部 8 人”），页面没有为每行
#    再发请求 —— 对应 annotate(employee_count=Count('employees')) 一次算出计数。
# 2. 页面现象：部门管理员侧边栏没有“部门管理”，硬敲 /departments/ 会看到
#    403 页面并列出所需权限 department:view —— 来自 @require_perm 的拦截。
# 3. 页面现象：搜索框输入“技术”后只剩匹配部门，地址带 ?q=技术；新增成功回到
#    列表并弹出绿色“部门新增成功”。
# 4. 页面现象：删除还有员工的部门时提示“该部门下仍有员工，无法删除” ——
#    外键 PROTECT 抛 ProtectedError，被视图捕获后转成中文提示。

from django.contrib import messages
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from app01.forms import DepartmentForm
from app01.middleware.permission import require_perm
from app01.models import Department
from app01.utils.pagination import paginate


@require_perm('department:view')
def department_list(request):
    keyword = request.GET.get('q', '').strip()
    queryset = Department.objects.annotate(employee_count=Count('employees')).order_by('id')
    if keyword:
        queryset = queryset.filter(title__icontains=keyword)
    page_obj, query_string = paginate(request, queryset, per_page=10)
    return render(
        request,
        'app01/department_list.html',
        {
            'page_obj': page_obj,
            'query_string': query_string,
            'keyword': keyword,
        },
    )


@require_perm('department:add')
def department_add(request):
    form = DepartmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '部门新增成功')
        return redirect('department_list')
    return render(
        request,
        'app01/department_form.html',
        {'form': form, 'title': '新增部门'},
    )


@require_perm('department:edit')
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '部门修改成功')
        return redirect('department_list')
    return render(
        request,
        'app01/department_form.html',
        {'form': form, 'title': '编辑部门', 'department': department},
    )


@require_perm('department:delete')
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method != 'POST':
        messages.error(request, '删除操作必须通过 POST 提交')
        return redirect('department_list')
    try:
        department.delete()
        messages.success(request, '部门删除成功')
    except ProtectedError:
        messages.error(request, '该部门下仍有员工，无法删除，请先转移员工')
    return redirect('department_list')
