# 企业员工管理系统（HRMS）

基于 Django 5.2 + MySQL 的企业员工管理系统课程设计项目。覆盖部门、员工、考勤、薪资、公告、任务六大业务模块，配套 RBAC 权限控制、数据统计图表，以及基于硅基流动大模型的 AI 智能助手。

> 完整版说明文档（数据库表设计、权限矩阵、功能验收清单、答辩要点）见 [项目说明书.md](项目说明书.md)。

## 技术栈

| 层次 | 技术 |
|---|---|
| 后端框架 | Django 5.2.19 |
| 数据库 | MySQL 8（`hrms` 库，utf8mb4 字符集），可切换 SQLite |
| 模板渲染 | Django Template + Bootstrap 3 |
| 前端交互 | jQuery + AJAX + ECharts |
| 图片处理 | Pillow（登录验证码、员工头像） |
| 大模型 | 硅基流动 SiliconFlow（OpenAI 兼容接口，默认 `Qwen/Qwen2.5-7B-Instruct`） |
| 配置管理 | python-dotenv（`.env` 存放密钥，不进 Git） |

## 功能列表

### 1. 登录与认证

- 用户名 + 密码 + 图片验证码登录
- 自定义 `LoginRequiredMiddleware`：未登录访问任何内页自动跳转 `/login/?next=原地址`
- 密码使用 Django PBKDF2 哈希存储，数据库不保存明文
- 会话有效期 14 天，支持退出登录

### 2. 首页概览

- 统计卡片：部门数、员工数、今日考勤情况、当月薪资总额
- ECharts 图表：部门人数分布、月度薪资趋势
- 后端只返回 JSON，前端渲染图表，数据与展示解耦

### 3. 部门管理

- 部门增删改查
- 按部门名称模糊搜索
- 分页展示（每页 10 条）
- 删除时保护：部门下仍有员工时禁止删除并提示

### 4. 员工管理

- 员工增删改查：姓名、年龄、性别、手机号、账户余额、入职日期、所属部门、头像
- 手机号唯一校验、年龄范围校验、手机号格式校验
- 头像上传保存到 `media/avatar/`
- 数据范围控制：
  - 超级管理员：全部员工
  - 部门管理员：仅本部门员工
  - 普通员工：仅本人档案
- 列表使用 `select_related` 消除 N+1 查询

### 5. 考勤管理

- 考勤记录增删改查
- 根据上下班打卡时间自动判定状态：按时 / 迟到 / 早退 / 缺勤
- 规则：09:00 上班、18:00 下班；未打卡视为缺勤
- 同一员工同一天只能有一条记录（数据库唯一约束）

### 6. 薪资管理

- 薪资记录增删改查
- 实发工资 = 基本工资 + 奖金 - 扣款，保存时自动计算
- 月份格式校验（YYYY-MM），同一员工同一月份唯一

### 7. 公告管理

- 公告发布、编辑、删除
- 支持置顶，置顶公告排在最前
- 发布时间自动记录

### 8. 任务管理（AJAX）

- 任务包含级别（高/中/低）、标题、详情、负责人
- 表单通过 AJAX 提交，页面不刷新，校验错误实时回显
- 提交成功后在列表顶部插入新记录

### 9. 权限管理（RBAC）

- 自定义用户模型 `app01.User`，用户 - 角色 - 权限三级模型
- 内置三个角色：超级管理员（全部权限）、部门管理员、普通员工
- 用户授权页：给用户分配角色
- 角色权限页：为角色勾选权限码
- 侧边栏菜单按权限动态渲染；视图层用 `@require_perm` 做接口级拦截，前后端双保险

### 10. AI 智能助手

- 右下角悬浮球：多轮对话，历史保存在 session（保留最近 10 轮）
- 数据感知：自动识别问题中的员工姓名，查询员工 / 考勤 / 薪资表，把真实数据注入提示词后回答
- 制度知识库问答：先按关键词检索知识库，再让模型"照着资料回答"，资料中没有则回答不知道
- 智能生成招聘 JD：输入岗位名称，三段式提示词生成结构化 JD
- 数据智能点评：读取指定员工的考勤与薪资数据，生成点评与改进建议
- 防呆设计：没有配置 API Key 时返回友好提示，不会导致页面报错

## 目录结构

```
program/
├── manage.py                     # Django 管理入口
├── requirements.txt              # 依赖清单
├── .env.example                  # 环境变量模板（复制为 .env 使用）
├── hrms/                         # 项目配置包
│   ├── settings.py               # 数据库、中间件、日志、媒体文件等配置
│   ├── urls.py                   # 根路由
│   └── wsgi.py / asgi.py
├── app01/                        # 业务应用
│   ├── models.py                 # 部门/员工/考勤/薪资/公告/任务/用户/角色/权限/知识库
│   ├── forms.py                  # 表单与校验
│   ├── urls.py                   # 业务路由
│   ├── views/                    # 视图：auth/dashboard/department/employee/attendance/
│   │                             #       salary/announcement/task/rbac/ai
│   ├── middleware/               # 登录拦截、权限装饰器
│   ├── utils/                    # AI 客户端、分页、验证码
│   ├── templatetags/rbac.py      # 模板权限标签
│   ├── management/commands/      # init_data（初始化）、demo_data（演示数据）
│   ├── templates/                # 页面模板
│   ├── static/                   # 本地 Bootstrap / jQuery / ECharts
│   └── migrations/               # 数据库迁移
├── media/                        # 用户上传文件（不进 Git）
└── logs/                         # 运行日志（不进 Git）
```

## 运行步骤

### 1. 准备环境

要求 Python 3.10+、MySQL 8（或直接使用 SQLite）。

```powershell
cd D:\ems\program

# 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 创建数据库

```sql
CREATE DATABASE hrms DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

数据库连接默认值为：库名 `hrms`、用户 `root`、密码 `123456`、地址 `127.0.0.1:3306`。
如需修改，可用环境变量 `DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT` 覆盖，例如：

```powershell
$env:DB_PASSWORD="你的密码"
```

不想装 MySQL 时，可改用 SQLite：

```powershell
$env:DB_ENGINE="sqlite"
```

### 3. 执行迁移并初始化数据

```powershell
python manage.py migrate        # 建表
python manage.py init_data      # 初始化权限、角色、超级管理员
python manage.py demo_data      # 写入演示数据（5 个部门、15 名员工、考勤、薪资、公告、任务、知识库）
```

两个初始化命令都是幂等的，可以重复执行，不会重复插入数据。

### 4. 配置 AI 助手（可选）

不配置也能正常使用系统，只是 AI 助手会提示"尚未配置 API Key"。

```powershell
copy .env.example .env
```

编辑 `.env`，填入在 https://cloud.siliconflow.cn/account/ak 申请的密钥：

```ini
SILICONFLOW_API_KEY=sk-你的密钥
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=Qwen/Qwen2.5-7B-Instruct
```

注意：`.env` 已被 `.gitignore` 排除，不会提交到仓库。

### 5. 启动服务

```powershell
python manage.py runserver 8000
```

浏览器访问 http://127.0.0.1:8000 ，会自动跳转到登录页。

如果同时还要运行其他 Django 项目，请换端口（例如 `runserver 8001`），避免端口冲突。

## 账号信息

| 账号 | 密码 | 角色 | 数据范围 |
|---|---|---|---|
| `admin` | `admin123456` | 超级管理员 | 全部模块、全部数据 |
| `manager01` | `manager123` | 部门管理员 | 技术部员工、考勤、薪资；公告与任务只读/可建 |
| `staff01` | `staff123` | 普通员工 | 仅本人档案、本人考勤、本人薪资 |

不同账号登录后侧边栏菜单条数不同，这是 RBAC 权限控制的直接体现。

修改密码：

```powershell
python manage.py changepassword admin
```

## 常用命令

| 命令 | 说明 |
|---|---|
| `python manage.py migrate` | 执行数据库迁移 |
| `python manage.py makemigrations` | 模型改动后生成迁移文件 |
| `python manage.py init_data` | 初始化权限、角色、超级管理员 |
| `python manage.py demo_data` | 写入演示数据 |
| `python manage.py changepassword <用户名>` | 重置指定用户密码 |
| `python manage.py check` | 检查项目配置 |
| `python manage.py runserver 8000` | 启动开发服务器 |

## 配置说明

`hrms/settings.py` 中可通过环境变量覆盖的配置：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DJANGO_SECRET_KEY` | 内置开发密钥 | 生产环境必须更换 |
| `DJANGO_DEBUG` | `True` | 设为 `False` 关闭调试模式 |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | 允许访问的域名 |
| `DB_ENGINE` | `mysql` | 设为 `sqlite` 使用 SQLite |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `hrms` / `root` / `123456` | 数据库连接 |
| `SILICONFLOW_API_KEY` | 空 | 硅基流动密钥 |

## 安全说明

- `.env`、`media/`、`logs/`、`__pycache__/`、`.idea/` 均已写入 `.gitignore`
- API Key 只从环境变量读取，代码中没有任何硬编码密钥
- 密码使用 PBKDF2 哈希存储
- 已开启 `X-Frame-Options: DENY`、`SECURE_CONTENT_TYPE_NOSNIFF`、`SESSION_COOKIE_HTTPONLY`
- 视图统一使用 ORM 参数化查询，避免 SQL 注入；模板默认转义，避免 XSS
