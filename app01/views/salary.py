"""薪资管理视图：CRUD、实发工资自动计算、按月份/员工筛选与总额统计。

职责（对应任务书 T7 薪资管理，涉及 T5 权限控制、T11 ORM 性能优化）：
薪资列表（月份 + 姓名 + 员工筛选、总额统计、分页）、新增、编辑、删除。
“实发工资 total”是只读计算字段（editable=False），
由 基本工资 + 奖金 - 扣款 得出，视图用 commit=False 先算再存，模型 save() 也兜底算一次。

术语：commit=False = form.save() 只生成对象不写库，便于补算字段后再 save()；
aggregate(Sum(...)) = SQL 聚合求和；select_related = JOIN 取关联数据，防 N+1。
"""

# 讲解要点：
# 1. 页面现象：薪资列表每行显示员工、部门、月份、基本工资、奖金、扣款和实发工资，
#    顶部显示“当前筛选总额” —— 总额来自 aggregate(Sum('total'))，只统计当前筛选结果。
# 2. 页面现象：新增薪资页没有“实发工资”输入框，填 5000 + 800 - 200 保存后列表
#    自动显示 5600 —— 因为视图用 commit=False 后调用 compute_total()，模型 save()
#    里又算了一遍，形成双重保障。
# 3. 页面现象：manager01 登录后薪资列表只有本部门记录、员工下拉框只有本部门员工；
#    staff01 登录后只看到自己的工资记录。
# 4. 页面现象：普通员工没有新增/编辑/删除按钮，改 URL 去编辑别人的薪资会看到
#    403“无权操作其他部门的薪资” —— 后端 _can_touch_salary 才是真正边界。

from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from app01.forms import SalaryForm
from app01.middleware.permission import require_perm
from app01.models import Salary
from app01.utils.pagination import paginate

from .common import is_department_scoped, scope_related_queryset, scoped_employees


def _can_touch_salary(user, salary):
    if user.is_super_admin or user.is_superuser:
        return True
    if is_department_scoped(user):
        return salary.employee.depart_id == user.depart_id
    return salary.employee.user_id == user.id


@require_perm('salary:view')
def salary_list(request):
    month = request.GET.get('month', '').strip()
    keyword = request.GET.get('q', '').strip()
    employee_id = request.GET.get('employee', '').strip()

    queryset = scope_related_queryset(
        request.user,
        Salary.objects.select_related('employee', 'employee__depart'),
    )
    if month:
        queryset = queryset.filter(month=month)
    if keyword:
        queryset = queryset.filter(employee__name__icontains=keyword)
    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)

    total_amount = queryset.aggregate(total=Sum('total'))['total'] or 0

    page_obj, query_string = paginate(request, queryset, per_page=10)
    return render(
        request,
        'app01/salary_list.html',
        {
            'page_obj': page_obj,
            'query_string': query_string,
            'month': month,
            'keyword': keyword,
            'employee_id': employee_id,
            'employees': scoped_employees(request.user),
            'total_amount': total_amount,
        },
    )


@require_perm('salary:add')
def salary_add(request):
    form = SalaryForm(request.POST or None)
    if is_department_scoped(request.user):
        form.fields['employee'].queryset = scoped_employees(request.user)
    if request.method == 'POST' and form.is_valid():
        salary = form.save(commit=False)
        salary.total = salary.compute_total()
        salary.save()
        messages.success(request, f'薪资新增成功，实发 {salary.total} 元')
        return redirect('salary_list')
    return render(
        request,
        'app01/salary_form.html',
        {'form': form, 'title': '新增薪资'},
    )


@require_perm('salary:edit')
def salary_edit(request, pk):
    salary = get_object_or_404(Salary, pk=pk)
    if not _can_touch_salary(request.user, salary):
        return HttpResponseForbidden('无权操作其他部门的薪资')

    form = SalaryForm(request.POST or None, instance=salary)
    if is_department_scoped(request.user):
        form.fields['employee'].queryset = scoped_employees(request.user)
    if request.method == 'POST' and form.is_valid():
        salary = form.save(commit=False)
        salary.total = salary.compute_total()
        salary.save()
        messages.success(request, '薪资修改成功')
        return redirect('salary_list')
    return render(
        request,
        'app01/salary_form.html',
        {'form': form, 'title': '编辑薪资', 'salary': salary},
    )


@require_perm('salary:delete')
def salary_delete(request, pk):
    salary = get_object_or_404(Salary, pk=pk)
    if not _can_touch_salary(request.user, salary):
        return HttpResponseForbidden('无权操作其他部门的薪资')
    if request.method != 'POST':
        messages.error(request, '删除操作必须通过 POST 提交')
        return redirect('salary_list')
    salary.delete()
    messages.success(request, '薪资记录删除成功')
    return redirect('salary_list')
