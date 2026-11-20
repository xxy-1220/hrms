"""写入演示数据，便于各模块界面展示与功能自测。（对应任务书 T1 初始化 / 演示数据）

用法：python manage.py demo_data

执行一次即可得到一套完整演示数据：5 个部门、15 名员工、两个演示账号、
最近 8 个工作日的考勤、最近 4 个月的薪资、4 条公告、5 条任务和 6 条制度知识库。
命令可重复执行，已存在的数据只更新不重复插入。
"""

# 讲解要点（结合浏览器里看到的页面效果）：
# 1. 执行 `python manage.py demo_data` 后再打开系统：部门页有 5 个部门、员工页有 15 人、
#    考勤页有近 8 个工作日的记录、薪资页有最近 4 个月的数据、公告页有 4 条、任务页有 5 条——
#    对应 handle() 里按「部门→员工→账号→考勤→薪资→公告→任务」顺序逐段写入。
# 2. 用 manager01 / manager123 登录只能看到技术部数据，用 staff01 / staff123 登录只能看到本人档案——
#    对应演示账号分别绑定 dept_admin / employee 角色，且 staff 账号与 employees[0] 关联。
# 3. 再执行一次 demo_data，各页面数据量不变，不会翻倍——对应 update_or_create / get_or_create 的幂等写法。
# 4. 每次执行生成的年龄、薪资、考勤状态都一样——对应 random.seed(2026) 固定了随机种子，演示结果可复现。

import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app01.models import (
    Announcement,
    Attendance,
    Department,
    Employee,
    Knowledge,
    Role,
    Salary,
    Task,
    User,
)

DEPARTMENTS = [
    ('技术部', '负责系统研发、运维与技术支持'),
    ('市场部', '负责市场推广、品牌与客户拓展'),
    ('人事部', '负责招聘、培训与员工关系'),
    ('财务部', '负责预算、核算与资金管理'),
    ('客服部', '负责客户咨询、售后与满意度维护'),
]

NAMES = [
    '张伟', '李娜', '王强', '赵敏', '刘洋',
    '陈静', '杨帆', '周杰', '吴倩', '徐磊',
    '孙悦', '马超', '朱琳', '胡军', '郭涛',
]

ANNOUNCEMENTS = [
    ('关于 2026 年第四季度绩效评审的通知', '各部门负责人请于本月底前完成本部门员工的绩效初评，并提交至人事部汇总。', True),
    ('系统升级维护公告', '本周六 22:00 - 次日 02:00 进行服务器升级，期间系统暂停访问，请提前保存工作内容。', True),
    ('中秋节福利发放安排', '公司将在下周三下午统一发放节日福利，请各部门安排人员到行政前台领取。', False),
    ('新员工入职培训通知', '本月新入职员工请于周五上午 9:30 到三楼会议室参加入职培训。', False),
]

TASK_TITLES = [
    ('high', '修复考勤统计口径问题', '核对迟到与早退的判定边界，输出修复方案。'),
    ('high', '完成薪资批量导入功能', '支持 Excel 导入并校验月份与员工唯一性。'),
    ('middle', '整理部门人员编制表', '统计各部门在职人数与空缺岗位。'),
    ('middle', '优化员工列表查询性能', '使用 select_related 消除列表页 N+1 查询。'),
    ('low', '更新系统使用手册', '补充 RBAC 权限说明与常见问题。'),
]

# T3 制度知识库预置数据：(分类, 标题, 内容, 关键词)
KNOWLEDGE_ITEMS = [
    (
        '考勤制度', '工作时间与打卡规定',
        '公司实行标准工时制，上班时间 9:00，下班时间 18:00，午休 12:00-13:00。'
        '员工每日需上下班各打卡一次；迟到超过 30 分钟按事假半天计；'
        '每月累计迟到 3 次以上扣减当月全勤奖；无故未打卡需在 3 个工作日内提交补卡申请。',
        '打卡,迟到,早退,全勤,补卡,上下班',
    ),
    (
        '考勤制度', '请假流程与审批权限',
        '请假需提前在系统提交申请：事假提前 1 天、病假当天补交病历、年假提前 3 天。'
        '1 天以内由部门经理审批，1-3 天由部门经理与人事部会签，3 天以上需总经理审批。'
        '病假需附医院证明；事假不计薪；年假按工龄计算，满 1 年 5 天、满 5 年 10 天。',
        '请假,事假,病假,年假,审批,流程',
    ),
    (
        '薪酬制度', '薪资构成与发放时间',
        '员工薪资由基本工资、绩效奖金、补贴与扣款组成，实发工资 = 基本工资 + 奖金 - 扣款。'
        '薪资于每月 10 日发放上月工资，遇节假日提前至最近工作日；'
        '薪资采用银行代发，如需查询明细可在系统「薪资管理」中查看。',
        '薪资,工资,奖金,扣款,发放,实发',
    ),
    (
        '薪酬制度', '年终奖计算规则',
        '年终奖与公司年度经营业绩及个人年度绩效挂钩，基准为 1-3 个月月薪。'
        '年度在职满 6 个月方可参与分配，不足 6 个月按实际在职月份折算；'
        '年度绩效为 D 级不发放年终奖；年终奖于次年春节前发放。',
        '年终奖,绩效,奖金,发放',
    ),
    (
        '人事制度', '新员工入职流程',
        '新员工入职需先提交身份证、学历证书、离职证明与体检报告，人事部审核后签订劳动合同。'
        '入职当天办理工牌、邮箱与系统账号，并参加为期半天的入职培训；'
        '试用期为 3 个月，试用期薪资为转正后的 80%。',
        '入职,试用期,劳动合同,培训,流程',
    ),
    (
        '人事制度', '离职申请与交接流程',
        '正式员工离职需提前 30 天提交书面申请，试用期员工提前 3 天。'
        '离职审批通过后需完成工作交接、资产归还与账号回收，'
        '人事部在交接完成后 15 个工作日内办理离职证明与社保减员。',
        '离职,交接,辞职,流程,证明',
    ),
]


class Command(BaseCommand):
    help = '写入部门、员工、考勤、薪资、公告、任务与制度知识库演示数据'

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2026)
        today = timezone.localdate()

        departments = []
        for title, description in DEPARTMENTS:
            department, _ = Department.objects.update_or_create(
                title=title, defaults={'description': description}
            )
            departments.append(department)
        self.stdout.write(self.style.SUCCESS(f'部门：{len(departments)} 个'))

        employees = []
        for index, name in enumerate(NAMES):
            phone = f'138000000{index + 1:02d}'
            employee, _ = Employee.objects.update_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'age': 24 + (index % 18),
                    'gender': 'female' if index % 2 else 'male',
                    'balance': Decimal(random.randint(1000, 20000)),
                    'hire_date': date(2020 + index % 4, (index % 12) + 1, (index % 24) + 1),
                    'depart': departments[index % len(departments)],
                },
            )
            employees.append(employee)
        self.stdout.write(self.style.SUCCESS(f'员工：{len(employees)} 人'))

        dept_admin_role = Role.objects.filter(code='dept_admin').first()
        employee_role = Role.objects.filter(code='employee').first()
        admin = User.objects.filter(is_super_admin=True).first()

        manager, created = User.objects.get_or_create(
            username='manager01',
            defaults={
                'first_name': '王',
                'last_name': '经理',
                'phone': '13900000001',
                'depart': departments[0],
                'is_staff': False,
            },
        )
        if created:
            manager.set_password('manager123')
            manager.save()
        if dept_admin_role:
            manager.roles.set([dept_admin_role])

        staff, created = User.objects.get_or_create(
            username='staff01',
            defaults={
                'first_name': '张',
                'last_name': '伟',
                'phone': employees[0].phone,
                'depart': employees[0].depart,
                'is_staff': False,
            },
        )
        if created:
            staff.set_password('staff123')
            staff.save()
        if employee_role:
            staff.roles.set([employee_role])
        if employees[0].user_id != staff.id:
            employees[0].user = staff
            employees[0].save(update_fields=['user'])

        self.stdout.write(self.style.SUCCESS(
            '演示账号：manager01 / manager123（部门管理员），'
            'staff01 / staff123（普通员工）'
        ))

        attendance_count = 0
        work_days = []
        cursor = today
        while len(work_days) < 8:
            if cursor.weekday() < 5:
                work_days.append(cursor)
            cursor -= timedelta(days=1)

        for employee in employees:
            for work_day in work_days:
                pattern = random.choice(['normal', 'normal', 'normal', 'late', 'early', 'absent'])
                if pattern == 'absent':
                    clock_in, clock_out = None, None
                elif pattern == 'late':
                    clock_in = time(9, random.randint(6, 30))
                    clock_out = time(18, random.randint(5, 40))
                elif pattern == 'early':
                    clock_in = time(8, random.randint(35, 58))
                    clock_out = time(17, random.randint(0, 45))
                else:
                    clock_in = time(8, random.randint(35, 58))
                    clock_out = time(18, random.randint(2, 30))

                Attendance.objects.update_or_create(
                    employee=employee,
                    date=work_day,
                    defaults={
                        'clock_in': clock_in,
                        'clock_out': clock_out,
                        'remark': '' if pattern == 'normal' else '演示数据',
                    },
                )
                attendance_count += 1
        self.stdout.write(self.style.SUCCESS(f'考勤记录：{attendance_count} 条'))

        salary_count = 0
        current_month = today.replace(day=1)
        months = []
        for offset in range(4):
            month = current_month
            for _ in range(offset):
                month = (month - timedelta(days=1)).replace(day=1)
            months.append(month.strftime('%Y-%m'))
        months.reverse()

        for employee in employees:
            for month in months:
                base = Decimal(random.randint(6000, 16000))
                bonus = Decimal(random.randint(0, 2000))
                deduction = Decimal(random.randint(0, 600))
                Salary.objects.update_or_create(
                    employee=employee,
                    month=month,
                    defaults={
                        'base_salary': base,
                        'bonus': bonus,
                        'deduction': deduction,
                    },
                )
                salary_count += 1
        self.stdout.write(self.style.SUCCESS(f'薪资记录：{salary_count} 条'))

        publisher = admin or manager
        for title, content, is_top in ANNOUNCEMENTS:
            Announcement.objects.update_or_create(
                title=title,
                defaults={
                    'content': content,
                    'is_top': is_top,
                    'publisher': publisher,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'公告：{len(ANNOUNCEMENTS)} 条'))

        for level, title, detail in TASK_TITLES:
            owner = random.choice(employees)
            Task.objects.get_or_create(
                title=title,
                defaults={
                    'level': level,
                    'detail': detail,
                    'owner': owner,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'任务：{len(TASK_TITLES)} 条'))

        for category, title, content, keywords in KNOWLEDGE_ITEMS:
            Knowledge.objects.update_or_create(
                title=title,
                defaults={
                    'category': category,
                    'content': content,
                    'keywords': keywords,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'知识库：{len(KNOWLEDGE_ITEMS)} 条'))
        self.stdout.write(self.style.SUCCESS('演示数据写入完成'))
