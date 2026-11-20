"""首页仪表盘与 ECharts 数据接口。（对应任务书 T10 图表统计）

本文件负责两件事：
- dashboard：渲染首页，准备统计卡片（员工数、部门数、今日考勤、本月薪资）和最新公告/任务；
- department_chart_data / salary_chart_data：给前端 ECharts 提供 JSON 数据，
  分别对应「部门人数饼图」和「各月薪资柱状图」。
"""

# 讲解要点（结合浏览器里看到的页面效果）：
# 1. 登录后进入首页，左侧卡片显示员工总数、部门数、今日出勤/异常、本月薪资合计——
#    对应 dashboard 里的 count()、exclude(...).count() 和 aggregate(total=Sum('total'))。
# 2. 页面上的「部门人数」饼图和「各月薪资」柱状图不是随 HTML 一起出来的，
#    而是在页面打开后由 JS 再发请求加载——对应 /stats/departments/、/stats/salaries/ 两个
#    JsonResponse 接口，返回的 JSON 被 ECharts 的 setOption 直接消费。
# 3. 用部门管理员 manager01 登录，饼图只剩自己部门的一条、卡片数字也变小——
#    对应 is_department_scoped(request.user) 与 scoped_employees(user) 的数据范围收窄。
# 4. 用没有 stats:view 权限的账号登录，首页图表区域隐藏/不加载——
#    对应 can_view_stats = user.has_perm_code('stats:view') 传给模板。

from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from app01.middleware.permission import require_perm
from app01.models import Announcement, Attendance, Department, Employee, Salary, Task

from .common import is_department_scoped, scope_related_queryset, scoped_employees


def dashboard(request):
    user = request.user
    today = timezone.localdate()
    current_month = today.strftime('%Y-%m')

    employees = scoped_employees(user)
    employee_count = employees.count()

    if is_department_scoped(user):
        department_count = Department.objects.filter(id=user.depart_id).count()
    else:
        department_count = Department.objects.count()

    today_attendances = Attendance.objects.filter(
        employee__in=employees, date=today
    )
    attendance_count = today_attendances.count()
    abnormal_count = today_attendances.exclude(status='normal').count()

    month_salary = Salary.objects.filter(
        employee__in=employees, month=current_month
    ).aggregate(total=Sum('total'))['total'] or 0

    announcements = Announcement.objects.select_related('publisher')[:5]
    tasks = Task.objects.select_related('owner', 'owner__depart')[:5]

    context = {
        'employee_count': employee_count,
        'department_count': department_count,
        'attendance_count': attendance_count,
        'abnormal_count': abnormal_count,
        'month_salary': month_salary,
        'current_month': current_month,
        'announcements': announcements,
        'tasks': tasks,
        'today': today,
        'can_view_stats': user.has_perm_code('stats:view'),
    }
    return render(request, 'app01/dashboard.html', context)


@require_perm('stats:view')
def department_chart_data(request):
    departments = Department.objects.annotate(count=Count('employees')).order_by('id')
    if is_department_scoped(request.user):
        departments = departments.filter(id=request.user.depart_id)

    data = [
        {'name': item.title, 'value': item.count}
        for item in departments
    ]
    return JsonResponse({'ok': True, 'data': data})


@require_perm('stats:view')
def salary_chart_data(request):
    queryset = scope_related_queryset(request.user, Salary.objects.all())
    rows = (
        queryset.values('month')
        .annotate(total=Sum('total'))
        .order_by('month')
    )
    labels = [row['month'] for row in rows]
    values = [float(row['total'] or 0) for row in rows]
    return JsonResponse({'ok': True, 'labels': labels, 'values': values})
