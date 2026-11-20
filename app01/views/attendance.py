"""考勤管理视图：CRUD，状态由上下班时间自动计算。

职责（对应任务书 T6 考勤管理，涉及 T5 权限控制、T11 ORM 性能优化）：
考勤列表（姓名 + 日期筛选、分页）、新增、编辑、删除。
“按时 / 迟到 / 早退 / 缺勤”不由用户手填，而是模型 Attendance.compute_status()
根据上下班时间自动算出（save() 时统一赋值），避免人工改状态作弊。

术语：select_related = 用 JOIN 一次取回员工与部门，防 N+1；数据范围 = 超管全部、
部门管理员本部门、普通员工仅本人。
"""

# 讲解要点：
# 1. 页面现象：考勤列表每行显示姓名、部门、日期、上下班时间和状态标签，按日期
#    筛选后只剩当天记录 —— 姓名/部门来自 select_related 的一次 JOIN。
# 2. 页面现象：manager01 登录后考勤列表只有本部门记录，staff01 登录后只有自己的
#    记录 —— 对应 scope_related_queryset 按“可见员工 id”过滤考勤表。
# 3. 页面现象：新增考勤时没有“考勤状态”输入框，填 9:10 上班、18:00 下班保存后
#    自动显示“迟到” —— 因为 Attendance.save() 调用了 compute_status()。
# 4. 页面现象：部门管理员新增考勤时员工下拉框只有本部门员工；改 URL 去编辑别部门
#    考勤会看到 403“无权操作其他部门的考勤”。

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from app01.forms import AttendanceForm
from app01.middleware.permission import require_perm
from app01.models import Attendance
from app01.utils.pagination import paginate

from .common import is_department_scoped, scope_related_queryset, scoped_employees


def _can_touch_attendance(user, attendance):
    if user.is_super_admin or user.is_superuser:
        return True
    if is_department_scoped(user):
        return attendance.employee.depart_id == user.depart_id
    return attendance.employee.user_id == user.id


@require_perm('attendance:view')
def attendance_list(request):
    keyword = request.GET.get('q', '').strip()
    date = request.GET.get('date', '').strip()

    queryset = scope_related_queryset(
        request.user,
        Attendance.objects.select_related('employee', 'employee__depart'),
    )
    if keyword:
        queryset = queryset.filter(employee__name__icontains=keyword)
    if date:
        queryset = queryset.filter(date=date)

    page_obj, query_string = paginate(request, queryset, per_page=10)
    return render(
        request,
        'app01/attendance_list.html',
        {
            'page_obj': page_obj,
            'query_string': query_string,
            'keyword': keyword,
            'date': date,
        },
    )


@require_perm('attendance:add')
def attendance_add(request):
    form = AttendanceForm(request.POST or None)
    if is_department_scoped(request.user):
        form.fields['employee'].queryset = scoped_employees(request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '考勤记录新增成功')
        return redirect('attendance_list')
    return render(
        request,
        'app01/attendance_form.html',
        {'form': form, 'title': '新增考勤'},
    )


@require_perm('attendance:edit')
def attendance_edit(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    if not _can_touch_attendance(request.user, attendance):
        return HttpResponseForbidden('无权操作其他部门的考勤')

    form = AttendanceForm(request.POST or None, instance=attendance)
    if is_department_scoped(request.user):
        form.fields['employee'].queryset = scoped_employees(request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '考勤记录修改成功')
        return redirect('attendance_list')
    return render(
        request,
        'app01/attendance_form.html',
        {'form': form, 'title': '编辑考勤', 'attendance': attendance},
    )


@require_perm('attendance:delete')
def attendance_delete(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    if not _can_touch_attendance(request.user, attendance):
        return HttpResponseForbidden('无权操作其他部门的考勤')
    if request.method != 'POST':
        messages.error(request, '删除操作必须通过 POST 提交')
        return redirect('attendance_list')
    attendance.delete()
    messages.success(request, '考勤记录删除成功')
    return redirect('attendance_list')
