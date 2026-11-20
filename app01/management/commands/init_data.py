"""初始化权限、角色与超级管理员账号。（对应任务书 T1 系统初始化）

用法：python manage.py init_data

这是项目第一次部署后必须执行的命令，一条命令完成三件事：
1. 写入 25 项权限（8 个模块 view/add/edit/delete 的子集，公告/任务/统计/系统按实际需要）；
2. 写入 3 个内置角色（超级管理员 / 部门管理员 / 普通员工）并给角色绑定权限；
3. 创建超级管理员账号 admin / admin123456。
命令可以重复执行，不会重复插入数据。
"""

# 讲解要点（结合浏览器里看到的页面效果）：
# 1. 第一次执行 `python manage.py init_data`，终端依次打印「权限初始化完成：25 项」、
#    「角色初始化完成：超级管理员（25 项权限）」等——对应下方 PERMISSIONS 列表和 ROLE_CONFIGS 字典。
# 2. 执行完用 admin / admin123456 登录，左侧菜单的部门、员工、考勤、薪资、公告、任务、统计、
#    系统管理全部可见——因为超级管理员的 permissions 是 '__all__'，拿到了全部权限。
# 3. 再执行一次 init_data，终端数字不变、数据库记录也不翻倍——对应 update_or_create 的「有则更新、无则新建」。
# 4. 用数据库工具查看 auth_user 表，admin 的 password 是 pbkdf2_sha256$... 开头的乱码——
#    对应 set_password 使用 Django 内置的 PBKDF2 哈希，数据库里永远不存明文密码。

from django.core.management.base import BaseCommand
from django.db import transaction

from app01.models import Permission, Role, User

PERMISSIONS = [
    ('department:view', '查看部门', '部门'),
    ('department:add', '新增部门', '部门'),
    ('department:edit', '编辑部门', '部门'),
    ('department:delete', '删除部门', '部门'),
    ('employee:view', '查看员工', '员工'),
    ('employee:add', '新增员工', '员工'),
    ('employee:edit', '编辑员工', '员工'),
    ('employee:delete', '删除员工', '员工'),
    ('attendance:view', '查看考勤', '考勤'),
    ('attendance:add', '新增考勤', '考勤'),
    ('attendance:edit', '编辑考勤', '考勤'),
    ('attendance:delete', '删除考勤', '考勤'),
    ('salary:view', '查看薪资', '薪资'),
    ('salary:add', '新增薪资', '薪资'),
    ('salary:edit', '编辑薪资', '薪资'),
    ('salary:delete', '删除薪资', '薪资'),
    ('announcement:view', '查看公告', '公告'),
    ('announcement:add', '发布公告', '公告'),
    ('announcement:edit', '编辑公告/置顶', '公告'),
    ('announcement:delete', '删除公告', '公告'),
    ('task:view', '查看任务', '任务'),
    ('task:add', '新增任务', '任务'),
    ('task:delete', '删除任务', '任务'),
    ('stats:view', '查看统计图表', '统计'),
    ('rbac:view', '查看权限管理', '系统'),
    ('rbac:manage', '管理用户角色权限', '系统'),
]

ROLE_CONFIGS = {
    '超级管理员': {
        'code': 'super_admin',
        'description': '拥有系统全部权限',
        'permissions': '__all__',
    },
    '部门管理员': {
        'code': 'dept_admin',
        'description': '管理本部门员工、考勤与薪资',
        'permissions': [
            'department:view',
            'employee:view', 'employee:add', 'employee:edit', 'employee:delete',
            'attendance:view', 'attendance:add', 'attendance:edit', 'attendance:delete',
            'salary:view', 'salary:add', 'salary:edit', 'salary:delete',
            'announcement:view',
            'task:view', 'task:add', 'task:delete',
            'stats:view',
        ],
    },
    '普通员工': {
        'code': 'employee',
        'description': '仅查看本人档案、考勤与薪资',
        'permissions': [
            'employee:view',
            'attendance:view', 'salary:view',
            'announcement:view', 'task:view',
        ],
    },
}


class Command(BaseCommand):
    help = '初始化权限、角色与超级管理员账号'

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name, module in PERMISSIONS:
            Permission.objects.update_or_create(
                code=code, defaults={'name': name, 'module': module}
            )
        self.stdout.write(self.style.SUCCESS(f'权限初始化完成：{len(PERMISSIONS)} 项'))

        for role_name, config in ROLE_CONFIGS.items():
            role, _ = Role.objects.update_or_create(
                code=config['code'],
                defaults={
                    'name': role_name,
                    'description': config['description'],
                },
            )
            if config['permissions'] == '__all__':
                permissions = Permission.objects.all()
            else:
                permissions = Permission.objects.filter(code__in=config['permissions'])
            role.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(
                f'角色初始化完成：{role_name}（{permissions.count()} 项权限）'
            ))

        admin_role = Role.objects.get(code='super_admin')
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'is_super_admin': True,
                'first_name': '系统',
                'last_name': '管理员',
                'email': 'admin@hrms.local',
            },
        )
        if created:
            # 使用 Django 内置 PBKDF2 哈希存储密码，严禁明文
            admin.set_password('admin123456')
            admin.save()
        admin.roles.set([admin_role])
        self.stdout.write(self.style.SUCCESS(
            '超级管理员账号：admin / admin123456'
        ))
        self.stdout.write(self.style.SUCCESS('初始化数据完成'))
