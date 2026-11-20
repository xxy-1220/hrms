"""员工管理视图：CRUD、模糊搜索、部门筛选、分页与头像上传。

职责（对应任务书 T3 员工管理，涉及 T5 权限控制、T11 ORM 性能优化、T13 安全加固）：
员工列表（姓名搜索 + 部门筛选 + 分页）、新增（含头像上传）、编辑、删除。
列表的数据范围来自 common.scoped_employees；单条记录的越权校验用 _can_touch_employee。

术语：ModelForm = 由模型自动生成表单并复用校验规则；request.FILES = 上传文件；
N+1 = 列表循环里逐行查外键，本项目用 select_related 一次性 JOIN 解决。
"""

# 讲解要点：
# 1. 页面现象：员工列表顶部有姓名搜索框和“全部部门”下拉框，输入“张”并选部门
#    后点“查询”，表格只剩符合条件的行，地址变成 /employees/?q=张&depart=3。
# 2. 页面现象：列表底部显示“共 N 条，第 1 / M 页”，每页正好 10 行，翻页后搜索
#    条件仍然保留 —— 因为 paginate 返回的 query_string 被拼进了翻页链接。
# 3. 页面现象：manager01 新增/编辑员工时部门下拉框只有本部门选项；手动改 URL
#    去编辑别部门员工会看到 403“无权操作其他部门的员工”。
# 4. 页面现象：staff01 登录后员工列表只有自己一行，且没有新增/编辑/删除按钮 ——
#    按钮隐藏靠模板标签，数据范围靠 scoped_employees，两者缺一不可。

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from app01.forms import EmployeeForm
from app01.middleware.permission import require_perm
from app01.models import Department, Employee
from app01.utils.pagination import paginate

from .common import is_department_scoped, scoped_employees


def _prepare_form_departments(request, form):
    if is_department_scoped(request.user):
        form.fields['depart'].queryset = Department.objects.filter(
            id=request.user.depart_id
        )


def _can_touch_employee(user, employee):
    if user.is_super_admin or user.is_superuser:
        return True
    if user.has_perm_code('employee:edit') and user.depart_id:
        return employee.depart_id == user.depart_id
    return employee.user_id == user.id


@require_perm('employee:view')
def employee_list(request):
    keyword = request.GET.get('q', '').strip()
    depart_id = request.GET.get('depart', '').strip()

    queryset = scoped_employees(request.user)
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    if depart_id:
        queryset = queryset.filter(depart_id=depart_id)

    page_obj, query_string = paginate(request, queryset, per_page=10)

    departments = Department.objects.all()
    if is_department_scoped(request.user):
        departments = departments.filter(id=request.user.depart_id)

    return render(
        request,
        'app01/employee_list.html',
        {
            'page_obj': page_obj,
            'query_string': query_string,
            'keyword': keyword,
            'depart_id': depart_id,
            'departments': departments,
        },
    )


@require_perm('employee:add')
def employee_add(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    _prepare_form_departments(request, form)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '员工新增成功')
        return redirect('employee_list')
    return render(
        request,
        'app01/employee_form.html',
        {'form': form, 'title': '新增员工'},
    )


@require_perm('employee:edit')
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if not _can_touch_employee(request.user, employee):
        return HttpResponseForbidden('无权操作其他部门的员工')

    form = EmployeeForm(
        request.POST or None, request.FILES or None, instance=employee
    )
    _prepare_form_departments(request, form)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '员工修改成功')
        return redirect('employee_list')
    return render(
        request,
        'app01/employee_form.html',
        {'form': form, 'title': '编辑员工', 'employee': employee},
    )


@require_perm('employee:delete')
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if not _can_touch_employee(request.user, employee):
        return HttpResponseForbidden('无权操作其他部门的员工')
    if request.method != 'POST':
        messages.error(request, '删除操作必须通过 POST 提交')
        return redirect('employee_list')
    employee.delete()
    messages.success(request, '员工删除成功')
    return redirect('employee_list')
