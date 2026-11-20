# 企业员工管理系统（HRMS）

基于 Django 5.2 + MySQL 的企业员工管理系统课程设计项目。覆盖部门、员工、考勤、薪资、公告、任务六大业务模块，配套 RBAC 权限控制、数据统计图表，以及基于硅基流动大模型的 AI 智能助手。

## 目录

1. [项目概述](#一项目概述)
2. [开发环境与技术栈](#二开发环境与技术栈)
3. [系统架构设计](#三系统架构设计)
4. [数据库设计](#四数据库设计)
5. [功能模块详解](#五功能模块详解)
6. [权限设计（RBAC）](#六权限设计rbac)
7. [AI 智能助手设计](#七ai-智能助手设计)
8. [运行部署步骤](#八运行部署步骤)
9. [功能自测与验收清单](#九功能自测与验收清单)
10. [账号信息](#十账号信息)
11. [常见问题](#十一常见问题)
12. [项目亮点与答辩要点](#十二项目亮点与答辩要点)
13. [安全说明](#十三安全说明)

---

## 一、项目概述

### 1.1 项目背景

企业员工管理系统（Human Resource Management System，简称 HRMS）用于解决中小企业人事管理中信息分散、纸质登记效率低、权限混乱等问题。系统把部门、员工档案、考勤、薪资、公告、任务六类核心业务集中到一个 Web 平台，并通过角色权限控制保证不同岗位只能访问自己职责范围内的数据。

### 1.2 项目目标

| 目标 | 说明 |
|---|---|
| 业务闭环 | 部门 → 员工 → 考勤 / 薪资 → 统计，形成完整数据链 |
| 权限可控 | 用户 - 角色 - 权限三级模型，菜单与接口双重校验 |
| 体验良好 | AJAX 异步提交、分页查询、图表可视化、逐字输出 |
| 智能增强 | 调用大模型 API 实现智能问答、JD 生成、数据点评 |
| 安全规范 | 密钥环境变量化、PBKDF2 密码、CSRF/XSS 防护 |

### 1.3 对应课程设计任务完成情况

| 任务 | 内容 | 完成情况 |
|---|---|---|
| T1 | 环境与 LLMClient 封装 | 已完成：`app01/utils/ai.py`，密钥走环境变量 |
| T2 | 智能生成招聘 JD | 已完成：`/ai/jd/`，三段式提示词 + AJAX 渲染 |
| T3 | 制度知识库问答 | 已完成：`Knowledge` 表 + 关键词检索 + `/ai/knowledge/` |
| T4 | 数据智能点评 | 已完成：`/ai/comment/`，读取真实考勤薪资数据 |
| T5 | 多轮对话助手 | 已完成：悬浮球，session 保存最近 10 轮 |
| T6 | 安全与健壮性 | 已完成：输入长度限制、超时重试、失败兜底 |
| T7 | 逐字输出 | 已完成：前端打字机效果，25ms/字 |

---

## 二、开发环境与技术栈

### 2.1 软件环境

| 项目 | 版本 / 说明 |
|---|---|
| 操作系统 | Windows 10 / 11 |
| Python | 3.10 及以上 |
| Django | 5.2.19 |
| 数据库 | MySQL 8.0（字符集 utf8mb4），可选 SQLite |
| 开发工具 | PyCharm / VS Code |
| 浏览器 | Chrome / Edge |

### 2.2 技术选型说明

| 层次 | 技术 | 选型理由 |
|---|---|---|
| 后端框架 | Django 5.2 | 自带 ORM、模板引擎、认证体系、安全中间件，适合快速完成管理系统 |
| 数据库 | MySQL 8 | 支持事务与外键约束，字符集 utf8mb4 可存中文与 emoji |
| 前端框架 | Bootstrap 3 | 栅格系统与组件开箱即用，无需构建工具 |
| 交互 | jQuery + AJAX | 实现表单无刷新提交与 JSON 数据交互 |
| 图表 | ECharts | 国内文档完善，配置式 API 上手快 |
| 图片处理 | Pillow | 动态生成登录验证码，处理员工头像 |
| 大模型 | 硅基流动 SiliconFlow | 提供 OpenAI 兼容接口，注册即送免费额度 |
| 密钥管理 | python-dotenv | `.env` 文件隔离密钥，配合 `.gitignore` 防止泄露 |

### 2.3 第三方依赖（requirements.txt）

```
Django==5.2.19
mysqlclient==2.3.0
Pillow==12.3.0
python-dotenv==1.0.1
```

---

## 三、系统架构设计

### 3.1 总体架构

系统采用 Django 的 MTV 分层：

```
浏览器（Bootstrap + jQuery + ECharts）
        │  HTTP / AJAX / JSON
        ▼
URLconf（app01/urls.py）  ── 路由分发
        ▼
中间件链（安全 → 会话 → CSRF → 认证 → 登录拦截）
        ▼
视图层（app01/views/*.py） ── 业务逻辑、权限校验
        ▼
模型层（app01/models.py）  ── ORM 映射
        ▼
MySQL 数据库（hrms）
```

### 3.2 请求处理流程

以「访问员工列表」为例：

1. 浏览器请求 `/employees/?page=2`
2. `LoginRequiredMiddleware` 检查 session，未登录则 302 跳转 `/login/?next=/employees/`
3. 路由匹配到 `employee_views.employee_list`
4. `@require_perm('employee:view')` 校验当前用户是否拥有该权限码，无权限返回 403 页面
5. `scoped_employees(user)` 按角色收窄数据范围
6. 分页组件切片查询（SQL 的 LIMIT/OFFSET）
7. 模板 `employee_list.html` 渲染，继承 `base.html` 公共布局

### 3.3 目录结构

```
program/
├── manage.py
├── requirements.txt
├── .env.example                  # 环境变量模板
├── hrms/                         # 配置包
│   ├── settings.py               # 数据库、中间件、日志、媒体、安全配置
│   ├── urls.py                   # 根路由
│   ├── wsgi.py / asgi.py
├── app01/                        # 业务应用
│   ├── models.py                 # 10 个数据模型
│   ├── forms.py                  # 表单定义与校验规则
│   ├── urls.py                   # 业务路由
│   ├── views/                    # 视图层
│   │   ├── auth.py               # 登录 / 注销 / 验证码
│   │   ├── dashboard.py          # 首页统计与图表接口
│   │   ├── department.py         # 部门管理
│   │   ├── employee.py           # 员工管理
│   │   ├── attendance.py         # 考勤管理
│   │   ├── salary.py             # 薪资管理
│   │   ├── announcement.py       # 公告管理
│   │   ├── task.py               # 任务管理（AJAX）
│   │   ├── rbac.py               # 用户授权 / 角色权限
│   │   ├── ai.py                 # AI 助手接口
│   │   └── common.py             # 数据范围公共逻辑
│   ├── middleware/
│   │   ├── login_required.py     # 全局登录拦截
│   │   └── permission.py         # 权限装饰器与白名单判断
│   ├── utils/
│   │   ├── ai.py                 # LLMClient 大模型封装
│   │   ├── pagination.py         # 分页组件
│   │   └── captcha.py            # 验证码生成
│   ├── templatetags/rbac.py      # 模板权限标签 has_perm_code
│   ├── management/commands/
│   │   ├── init_data.py          # 初始化权限、角色、管理员
│   │   └── demo_data.py          # 写入演示数据
│   ├── templates/                # 页面模板
│   ├── static/                   # 本地 Bootstrap / jQuery / ECharts
│   └── migrations/               # 数据库迁移文件
├── media/                        # 上传文件（不进 Git）
└── logs/                         # 运行日志（不进 Git）
```

### 3.4 公共机制

**登录拦截中间件**：放行 `/login/`、`/logout/`、`/captcha/`、`/static/`、`/media/`、`/admin/`，其余路径未登录一律跳转登录页，避免每个视图重复写装饰器。

**权限装饰器**：`@require_perm('模块:动作')`，在视图执行前校验权限码，无权限返回 403 并列出所需权限。

**模板权限标签**：`{% has_perm_code request.user 'employee:add' as can_add %}`，控制按钮是否渲染，实现"前端隐藏 + 后端拦截"双保险。

**分级日志**：业务日志写入 `logs/hrms.log`，错误单独写入 `logs/error.log`，单文件 5MB 轮转、保留 5 份。

---

## 四、数据库设计

数据库名 `hrms`，字符集 `utf8mb4`，共 10 张业务表（不含 Django 内置表）。

### 4.1 部门表 app01_department

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键自增 | 部门编号 |
| title | varchar(50) | 唯一，至少 2 字符 | 部门名称 |
| description | text | 可空 | 部门描述 |
| created_at | datetime | 自动写入 | 创建时间 |

### 4.2 员工表 app01_employee

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 员工编号 |
| name | varchar(20) | 2~20 字符 | 姓名 |
| age | smallint | 18~65 | 年龄 |
| gender | varchar(10) | male / female | 性别 |
| balance | decimal(10,2) | ≥ 0 | 账户余额 |
| hire_date | date | 默认当天 | 入职日期 |
| phone | varchar(11) | 唯一，`^1[3-9]\d{9}$` | 手机号 |
| depart_id | bigint | 外键 → 部门，PROTECT | 所属部门 |
| avatar | image | 可空，上传至 `avatar/年/月/` | 头像 |
| user_id | bigint | 外键 → 用户，可空 | 关联登录账号 |
| created_at | datetime | 自动写入 | 创建时间 |

说明：`PROTECT` 保证部门下还有员工时不允许删除部门。

### 4.3 考勤表 app01_attendance

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 记录编号 |
| employee_id | bigint | 外键 → 员工，CASCADE | 员工 |
| date | date | 与员工联合唯一 | 考勤日期 |
| clock_in | time | 可空 | 上班打卡时间 |
| clock_out | time | 可空 | 下班打卡时间 |
| status | varchar(10) | 系统计算 | normal / late / early / absent |
| remark | varchar(200) | 可空 | 备注 |

**状态自动判定规则**（保存时执行）：

- 未打卡（任一为空）→ 缺勤
- 上班晚于 09:00 → 迟到
- 下班早于 18:00 → 早退
- 其余 → 按时

### 4.4 薪资表 app01_salary

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 记录编号 |
| employee_id | bigint | 外键 → 员工，CASCADE | 员工 |
| month | varchar(7) | 格式 `YYYY-MM`，与员工联合唯一 | 月份 |
| base_salary | decimal(10,2) | 默认 0 | 基本工资 |
| bonus | decimal(10,2) | 默认 0 | 奖金 |
| deduction | decimal(10,2) | 默认 0 | 扣款 |
| total | decimal(10,2) | 系统计算，不可编辑 | 实发工资 |
| created_at | datetime | 自动写入 | 创建时间 |

**计算公式**：实发工资 = 基本工资 + 奖金 - 扣款，保存时自动写入，表单中不可手填。

### 4.5 公告表 app01_announcement

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 公告编号 |
| title | varchar(100) | 必填 | 标题 |
| content | text | 必填 | 正文 |
| publisher_id | bigint | 外键 → 用户，可空 | 发布人 |
| publish_time | datetime | 自动写入 | 发布时间 |
| is_top | boolean | 默认 False | 是否置顶 |

排序规则：`-is_top`（置顶优先）、`-publish_time`（新的在前）。

### 4.6 任务表 app01_task

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 任务编号 |
| level | varchar(10) | high / middle / low | 级别（高/中/低） |
| title | varchar(50) | 必填 | 标题 |
| detail | text | 必填 | 详情 |
| owner_id | bigint | 外键 → 员工，CASCADE | 负责人 |
| created_at | datetime | 自动写入 | 创建时间 |

### 4.7 权限表 app01_permission

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 权限编号 |
| code | varchar(50) | 唯一 | 权限码，如 `employee:edit` |
| name | varchar(50) | 必填 | 权限名称 |
| module | varchar(20) | 必填 | 所属模块 |

### 4.8 角色表 app01_role

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 角色编号 |
| name | varchar(30) | 唯一 | 角色名称 |
| code | varchar(30) | 唯一 | 角色编码 |
| description | varchar(200) | 可空 | 角色描述 |
| permissions | 多对多 | 关联权限表 | 角色拥有的权限 |

### 4.9 用户表 app01_user

继承 Django `AbstractUser`，额外字段：

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| phone | varchar(11) | 可空 | 手机号 |
| depart_id | bigint | 外键 → 部门，可空，SET_NULL | 所属部门 |
| roles | 多对多 | 关联角色表 | 用户拥有的角色 |
| is_super_admin | boolean | 默认 False | 是否超级管理员 |

说明：`AUTH_USER_MODEL = 'app01.User'`，必须在首次迁移前配置。

### 4.10 知识库表 app01_knowledge

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | 主键 | 条目编号 |
| category | varchar(30) | 默认"制度" | 分类（考勤/薪酬/人事等） |
| title | varchar(100) | 必填 | 制度标题 |
| content | text | 必填 | 制度正文 |
| keywords | varchar(200) | 可空 | 检索关键词，逗号分隔 |
| created_at | datetime | 自动写入 | 创建时间 |

### 4.11 表间关系

```
部门 1 ──── n 员工
员工 1 ──── n 考勤
员工 1 ──── n 薪资
员工 1 ──── n 任务（负责人）
用户 n ──── n 角色（多对多）
角色 n ──── n 权限（多对多）
用户 1 ──── 1 员工（可空，普通员工账号关联本人档案）
用户 1 ──── n 公告（发布人）
```

---

## 五、功能模块详解

### 5.1 登录与认证模块

**访问路径**：`/login/`

**页面组成**：用户名输入框、密码输入框、图片验证码、登录按钮。

**操作流程**：

1. 打开系统任意地址，未登录自动跳转登录页
2. 输入账号密码与验证码，点击登录
3. 校验顺序：非空校验 → 验证码校验（不区分大小写，校验后立即失效防重放）→ 密码哈希比对
4. 成功后写入 session 并跳转首页；失败回到登录页显示错误提示

**技术要点**：

- 验证码由 Pillow 动态生成，随机字符存入 session
- 密码使用 Django 内置 PBKDF2 哈希，数据库中不存明文
- 登录拦截由 `LoginRequiredMiddleware` 统一处理，登录后可通过 `?next=` 回到原访问地址

### 5.2 首页概览模块

**访问路径**：`/`

**页面组成**：

- 四张统计卡片：员工总数、部门数量、今日考勤人数、本月薪资合计
- 部门人数饼图、各月薪资柱状图
- 最新公告列表、最新任务列表

**技术要点**：

- 统计使用 ORM 聚合：`count()`、`Sum('total')`
- 图表数据由 `/stats/departments/`、`/stats/salaries/` 两个 JSON 接口提供
- 数据随角色收窄：部门管理员只统计本部门，普通员工只统计本人
- 无 `stats:view` 权限时图表区域不加载

### 5.3 部门管理模块

**访问路径**：`/departments/`

**功能清单**：

| 操作 | 路径 | 权限码 |
|---|---|---|
| 查看列表 | `/departments/` | department:view |
| 新增部门 | `/departments/add/` | department:add |
| 编辑部门 | `/departments/<id>/edit/` | department:edit |
| 删除部门 | `/departments/<id>/delete/` | department:delete |

**功能说明**：

- 列表显示部门名称与人数统计（`annotate(Count('employees'))` 一次查询完成）
- 支持按名称模糊搜索，搜索条件在翻页时保留
- 分页展示
- 删除保护：部门下仍有员工时提示"该部门下仍有员工，无法删除"

### 5.4 员工管理模块

**访问路径**：`/employees/`

**功能清单**：增删改查，路径规则同上。

**表单字段与校验**：

| 字段 | 校验规则 |
|---|---|
| 姓名 | 2~20 个字符 |
| 年龄 | 18~65 岁 |
| 手机号 | 唯一，且符合 `1[3-9]xxxxxxxxx` |
| 余额 | 不能为负数 |
| 部门 | 必选（下拉框） |
| 头像 | 图片文件，保存到 `media/avatar/年/月/` |

**数据范围（重点）**：

| 角色 | 可见数据 |
|---|---|
| 超级管理员 | 全部员工 |
| 部门管理员 | 仅本部门员工（未绑定部门时返回空列表） |
| 普通员工 | 仅本人档案 |

**性能优化**：列表查询使用 `select_related('depart')`，一次 JOIN 取回部门，避免 N+1 查询。

### 5.5 考勤管理模块

**访问路径**：`/attendances/`

**功能说明**：

- 录入员工上下班打卡时间，系统自动判定状态
- 同一员工同一天只能有一条记录（数据库唯一约束）
- 列表按日期倒序展示，迟到/早退/缺勤有状态标识
- 普通员工只能查看本人考勤

### 5.6 薪资管理模块

**访问路径**：`/salaries/`

**功能说明**：

- 录入基本工资、奖金、扣款，实发工资自动计算
- 月份格式校验 `YYYY-MM`，同一员工同一月唯一
- 列表显示各月薪资明细
- 普通员工只能查看本人薪资

### 5.7 公告管理模块

**访问路径**：`/announcements/`

**功能说明**：

- 发布、编辑、删除公告
- 支持一键置顶/取消置顶
- 发布时间自动记录，无需手填
- 置顶公告在列表和首页中优先显示

### 5.8 任务管理模块（AJAX）

**访问路径**：`/tasks/`

**功能说明**：

- 任务包含级别（高/中/低）、标题、详情、负责人
- 表单通过 AJAX 提交，页面**不刷新**
- 校验失败时错误信息显示在对应输入框下方，已填内容保留
- 创建成功后新任务插入列表顶部，并提示"任务创建成功"
- 删除任务通过 AJAX 请求完成

**接口约定**：

```
POST /tasks/create/   → {"ok": true, "html": "<新行HTML>", "message": "任务创建成功"}
                      → {"ok": false, "errors": {"title": ["标题不能为空"]}}

POST /tasks/<id>/delete/ → {"ok": true}
```

### 5.9 权限管理模块（RBAC）

**访问路径**：`/system/users/`、`/system/roles/`

**功能说明**：

- 用户授权：为每个用户勾选角色
- 角色权限：为每个角色勾选权限码
- 侧边栏菜单根据当前用户权限动态渲染，无权限的菜单不显示
- 直接输入 URL 访问无权限页面会被拦截并返回 403

### 5.10 AI 智能助手模块

**访问入口**：任何业务页面右下角的悬浮球，以及侧边栏「AI 智能助手」页面。

详见[第七章](#七ai-智能助手设计)。

---

## 六、权限设计（RBAC）

### 6.1 三级模型

```
用户 User ──(多对多)── 角色 Role ──(多对多)── 权限 Permission
```

- 一个用户可以拥有多个角色
- 一个角色可以拥有多个权限
- 用户最终权限 = 所属所有角色权限的并集
- 超级管理员（`is_super_admin=True`）直接拥有全部权限

### 6.2 内置角色

| 角色 | 编码 | 说明 |
|---|---|---|
| 超级管理员 | super_admin | 拥有系统全部权限 |
| 部门管理员 | dept_admin | 管理本部门员工、考勤、薪资；可建任务；查看公告与统计 |
| 普通员工 | employee | 仅查看本人档案、本人考勤、本人薪资、公告、任务 |

### 6.3 权限码清单（26 项）

| 模块 | 权限码 | 说明 |
|---|---|---|
| 部门 | department:view / add / edit / delete | 查看、新增、编辑、删除 |
| 员工 | employee:view / add / edit / delete | 查看、新增、编辑、删除 |
| 考勤 | attendance:view / add / edit / delete | 查看、新增、编辑、删除 |
| 薪资 | salary:view / add / edit / delete | 查看、新增、编辑、删除 |
| 公告 | announcement:view / add / edit / delete | 查看、发布、编辑/置顶、删除 |
| 任务 | task:view / add / delete | 查看、新增、删除 |
| 统计 | stats:view | 查看图表统计 |
| 系统 | rbac:view / rbac:manage | 查看权限管理、管理用户角色权限 |

### 6.4 角色权限矩阵

| 权限码 | 超级管理员 | 部门管理员 | 普通员工 |
|---|:---:|:---:|:---:|
| department:view | ✓ | ✓ | |
| department:add / edit / delete | ✓ | | |
| employee:view | ✓ | ✓ | ✓ |
| employee:add / edit / delete | ✓ | ✓ | |
| attendance:view | ✓ | ✓ | ✓ |
| attendance:add / edit / delete | ✓ | ✓ | |
| salary:view | ✓ | ✓ | ✓ |
| salary:add / edit / delete | ✓ | ✓ | |
| announcement:view | ✓ | ✓ | ✓ |
| announcement:add / edit / delete | ✓ | | |
| task:view | ✓ | ✓ | ✓ |
| task:add / delete | ✓ | ✓ | |
| stats:view | ✓ | ✓ | |
| rbac:view / rbac:manage | ✓ | | |

### 6.5 两层校验机制

| 层次 | 实现 | 作用 |
|---|---|---|
| 前端 | 模板标签 `has_perm_code` | 无权限的菜单项和按钮直接不渲染 |
| 后端 | 装饰器 `@require_perm` | 直接访问 URL 也会被拦截返回 403 |

---

## 七、AI 智能助手设计

### 7.1 功能组成

| 功能 | 入口 | 说明 |
|---|---|---|
| 智能对话 | 右下角悬浮球 | 多轮对话，自动查库作答 |
| 招聘 JD 生成 | `/ai/jd/` | 输入岗位名称，生成结构化 JD |
| 制度知识库问答 | `/ai/knowledge/` | 检索制度后回答，展示命中条目 |
| 数据智能点评 | `/ai/comment/` | 分析员工考勤薪资并给出建议 |

### 7.2 技术架构

```
浏览器（悬浮球 / 页面）
   │  AJAX POST
   ▼
views/ai.py ── 解析问题 → 查询本地数据库 → 组装提示词
   │
   ▼
utils/ai.py（LLMClient）── HTTPS 调用硅基流动 /v1/chat/completions
   │
   ▼
返回文本 → 前端逐字渲染
```

### 7.3 数据感知机制（核心设计）

大模型本身看不到数据库，传统做法只会回答"请提供工号"。本系统在调用模型前先做本地检索：

1. 用正则从问题中提取 2~4 个汉字的候选词
2. 用候选词查员工表 `name__icontains`
3. 命中员工后，再查其最近 5 条考勤、最近 3 条薪资
4. 把这些真实数据作为"参考资料"拼进系统提示词

示例：提问"张伟的考勤怎么样"

```
### 相关员工数据
【员工】张伟（男，26岁，部门：技术部，入职：2022-03-15）
  最近考勤：
    2026-11-20 normal
    2026-11-19 late
    ...
```

模型据此直接回答，不会编造。**没有匹配到员工时不拼接任何员工数据**，避免答非所问。

### 7.4 知识库问答机制

1. 把问题按标点切分，提取长度 ≥ 2 的中文词
2. 在 `Knowledge` 表中按标题和正文做关键词匹配，最多取 5 条
3. 提示词中明确要求："资料里没有答案就说知识库中暂无相关制度，不要编造"
4. 页面同时展示"AI 回答"和"命中的制度条目"，方便验证回答依据

### 7.5 多轮对话

- 历史保存在 session 的 `ai_floating_history` 中
- 只保存用户的提问和模型的回答，不保存每次拼接的系统提示词，节省 token
- 最多保留最近 10 轮，超出后丢弃最早内容

### 7.6 配置方式

`.env` 文件（已在 `.gitignore` 中排除）：

```ini
SILICONFLOW_API_KEY=sk-你的密钥
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=Qwen/Qwen2.5-7B-Instruct
```

密钥申请地址：https://cloud.siliconflow.cn/account/ak

说明：`utils/ai.py` 每次调用时才从 `os.environ` 读取配置，并用 `load_dotenv(override=True)` 加载，保证修改 `.env` 后无需改代码即可生效。

### 7.7 健壮性设计（T6）

| 风险 | 处理方式 |
|---|---|
| 未配置 Key | 返回友好提示，页面不报错 |
| 网络超时 | 超时 30 秒，失败自动重试 2 次 |
| 返回格式异常 | 捕获 KeyError，提示"模型返回格式异常" |
| 超长输入 | 单条问题截断到 500 字 |
| 逐字输出 | 前端 25ms/字渲染，可随时调整速度 |

---

## 八、运行部署步骤

### 8.1 第一步：准备 Python 环境

```powershell
cd D:\ems\program

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（PowerShell）
.venv\Scripts\Activate.ps1

# 如果提示"禁止运行脚本"，先执行：
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 8.2 第二步：安装依赖

```powershell
pip install -r requirements.txt
```

若 `mysqlclient` 安装失败（缺少编译环境），可改用 SQLite 模式，见 8.7。

### 8.3 第三步：创建数据库

使用 Navicat / MySQL 命令行执行：

```sql
CREATE DATABASE hrms DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

默认连接参数（可在 `hrms/settings.py` 或环境变量中修改）：

| 参数 | 默认值 |
|---|---|
| 库名 | hrms |
| 用户 | root |
| 密码 | 123456 |
| 地址 | 127.0.0.1 |
| 端口 | 3306 |

### 8.4 第四步：执行迁移

```powershell
python manage.py migrate
```

执行成功后数据库中会创建所有业务表。

### 8.5 第五步：初始化数据

```powershell
python manage.py init_data    # 权限 26 项 + 3 个角色 + 超级管理员
python manage.py demo_data    # 5 部门、15 员工、考勤、薪资、公告、任务、知识库
```

两个命令均可重复执行，不会产生重复数据。

执行后会自动创建：

- 26 项权限码（部门 / 员工 / 考勤 / 薪资 / 公告 / 任务 / 统计 / 系统 八个模块）
- 3 个角色：超级管理员（26 项权限）、部门管理员（18 项权限）、普通员工（5 项权限）
- 超级管理员账号 `admin`，初始密码 `admin123456`
- 演示数据：5 个部门、15 名员工、考勤与薪资记录、公告、任务、制度知识库条目

### 8.6 第六步：配置 AI（可选）

```powershell
copy .env.example .env
```

编辑 `.env` 填入自己的硅基流动密钥。不配置也能运行，只是 AI 助手会提示未配置。

### 8.7 第七步：启动

```powershell
python manage.py runserver 8000
```

浏览器访问 http://127.0.0.1:8000 ，自动跳转登录页。

**使用 SQLite（不装 MySQL 的方案）**：

```powershell
$env:DB_ENGINE="sqlite"
python manage.py migrate
python manage.py init_data
python manage.py demo_data
python manage.py runserver 8000
```

### 8.8 PyCharm 中运行

1. `File → Settings → Project → Python Interpreter`，选择 `.venv` 下的解释器
2. `Run → Edit Configurations → + → Django Server`
3. 设置：
   - **Working directory**：`D:\ems\program`
   - **Parameters**：`runserver 8000`
4. 点击运行

注意：如果同时还要运行其他 Django 项目，必须换端口（如 `runserver 8001`），否则两个项目会抢同一个端口，浏览器只能访问到其中一个。

### 8.9 常用命令

| 命令 | 说明 |
|---|---|
| `python manage.py migrate` | 执行数据库迁移 |
| `python manage.py makemigrations` | 模型改动后生成迁移文件 |
| `python manage.py init_data` | 初始化权限、角色、超级管理员 |
| `python manage.py demo_data` | 写入演示数据 |
| `python manage.py changepassword <用户名>` | 重置指定用户密码 |
| `python manage.py check` | 检查项目配置 |
| `python manage.py runserver 8000` | 启动开发服务器 |

### 8.10 可通过环境变量覆盖的配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DJANGO_SECRET_KEY` | 内置开发密钥 | 生产环境必须更换 |
| `DJANGO_DEBUG` | `True` | 设为 `False` 关闭调试模式 |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | 允许访问的域名 |
| `DB_ENGINE` | `mysql` | 设为 `sqlite` 使用 SQLite |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `hrms` / `root` / `123456` | 数据库连接 |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | 数据库地址与端口 |
| `SILICONFLOW_API_KEY` | 空 | 硅基流动密钥 |
| `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` | 接口地址 |
| `SILICONFLOW_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | 模型名称 |

---

## 九、功能自测与验收清单

建议按以下顺序演示，每条都能在 1 分钟内完成。

| 序号 | 功能点 | 操作步骤 | 预期结果 |
|---|---|---|---|
| 1 | 未登录拦截 | 未登录直接访问 `/employees/` | 自动跳转登录页，地址带 `?next=/employees/` |
| 2 | 验证码 | 输入错误验证码登录 | 提示"验证码错误"，验证码自动刷新 |
| 3 | 登录成功 | 用 admin / admin123456 登录 | 进入首页，侧边栏显示全部菜单 |
| 4 | 首页统计 | 观察首页卡片与图表 | 显示员工数、部门数、今日考勤、本月薪资；饼图与柱状图有数据 |
| 5 | 部门新增 | 部门管理 → 新增部门 | 列表出现新部门，提示新增成功 |
| 6 | 部门删除保护 | 删除"技术部" | 提示该部门下仍有员工，无法删除 |
| 7 | 部门搜索分页 | 搜索"部"字 | 只显示匹配部门，翻页后搜索条件保留 |
| 8 | 员工数据范围 | 用 manager01 登录看员工列表 | 只显示技术部员工 |
| 9 | 员工数据范围 | 用 staff01 登录看员工列表 | 只显示张伟本人 |
| 10 | 员工校验 | 新增员工时手机号填错格式 | 表单下方显示手机号格式错误 |
| 11 | 头像上传 | 新增员工并上传图片 | 列表显示头像，文件保存在 `media/avatar/` |
| 12 | 考勤自动判定 | 新增考勤，上班时间填 09:30 | 状态自动显示"迟到" |
| 13 | 考勤唯一约束 | 同一员工同一天再录一次 | 提示该记录已存在 |
| 14 | 薪资自动计算 | 基本 8000、奖金 1000、扣款 500 | 实发自动显示 8500，表单不能手填 |
| 15 | 公告置顶 | 勾选置顶并保存 | 该公告排在列表最前，首页也优先显示 |
| 16 | 任务 AJAX | 任务管理填写表单提交 | 页面不刷新，新任务出现在列表顶部 |
| 17 | 任务校验 | 标题留空提交 | 标题输入框下方显示错误，已填内容不丢 |
| 18 | 权限菜单 | 用 manager01 登录 | 侧边栏无"系统管理" |
| 19 | 接口级拦截 | staff01 手动访问 `/departments/` | 显示 403 页面，列出所需权限 |
| 20 | 图表接口 | 访问 `/stats/departments/` | 返回 JSON 数据 |
| 21 | AI 悬浮球 | 点击右下角紫色圆形按钮 | 弹出对话面板 |
| 22 | AI 数据感知 | 问"张伟的考勤怎么样" | 直接给出张伟的考勤情况，而不是让提供工号 |
| 23 | AI 多轮对话 | 接着问"他迟到了几次" | 能理解"他"指张伟 |
| 24 | AI 知识库 | 问"请假流程是什么" | 依据知识库回答，下方显示命中的制度条目 |
| 25 | AI 逐字输出 | 观察 AI 回复过程 | 文字一个字一个字出现 |
| 26 | AI 兜底 | 不配置 Key 时提问 | 提示尚未配置 API Key，页面不报错 |
| 27 | 账号隔离 | 退出后分别用三个账号登录 | 侧边栏菜单条数依次减少 |

---

## 十、账号信息

| 账号 | 密码 | 角色 | 数据范围 |
|---|---|---|---|
| `admin` | `admin123456` | 超级管理员 | 全部模块、全部数据 |
| `manager01` | `manager123` | 部门管理员 | 技术部员工、考勤、薪资；可建任务；查看公告与统计 |
| `staff01` | `staff123` | 普通员工 | 仅本人档案、本人考勤、本人薪资 |

补充说明：

- 三个账号由 `init_data` 和 `demo_data` 创建，密码均为脚本中定义的初始密码
- 若密码被修改过，可用 `python manage.py changepassword admin` 重置
- 登录时需填写验证码，验证码不区分大小写

---

## 十一、常见问题

**Q1：启动时报 "That port is already in use"**
端口被占用。换一个端口启动：`python manage.py runserver 8001`；或找到占用 8000 的进程结束掉。

**Q2：同一台电脑启动两个 Django 项目，浏览器只显示其中一个？**
两个项目用了相同端口。必须给第二个换端口，并且浏览器地址栏也要改成对应端口。

**Q3：迁移时报 "Table 'xxx' already exists"**
数据库里已有旧表。删库重建，或执行 `python manage.py migrate --fake-initial`。

**Q4：登录提示用户名或密码错误**
执行 `python manage.py changepassword 用户名` 重置密码。注意本项目的密码是 PBKDF2 哈希，无法从数据库反查明文。

**Q5：AI 助手提示"尚未配置硅基流动 API Key"**
检查项目根目录是否有 `.env` 文件、`SILICONFLOW_API_KEY` 是否填写完整。修改后无需重启（每次调用重新读取），但建议重启以确保生效。

**Q6：员工头像显示不出来**
确认 `settings.py` 中 `MEDIA_URL`、`MEDIA_ROOT` 正确，且 `urls.py` 中配置了 media 路由（DEBUG 模式下由 Django 提供文件服务）。

**Q7：`pip install mysqlclient` 失败**
Windows 缺少编译环境。两种方案：安装 `mysqlclient` 的预编译 wheel，或改用 SQLite：`$env:DB_ENGINE="sqlite"`。

**Q8：侧边栏菜单不全**
当前账号角色权限不足。用 admin 登录，在「系统管理 → 用户授权」中给账号分配对应角色。

---

## 十二、项目亮点与答辩要点

### 12.1 技术亮点

1. **数据范围控制集中在公共模块**
   `views/common.py` 中 `scoped_employees` 统一处理三种角色的数据边界，避免各视图各写一套导致越权漏洞。

2. **前后端双层权限校验**
   模板标签隐藏菜单与按钮，装饰器拦截直接 URL 访问，两层配合防止绕过。

3. **业务规则下沉到模型层**
   考勤状态、薪资实发金额都在 `save()` 中自动计算，任何入口写入都保证数据一致。

4. **AJAX 无刷新交互**
   任务模块实现校验错误实时回显，提交成功后局部更新，体验接近单页应用。

5. **AI 不只是"聊天框"**
   通过本地检索把真实业务数据注入提示词，让模型能回答"张伟考勤如何"这类需要数据支撑的问题，而不是只会说套话。

6. **工程化细节**
   密钥环境变量化、`.gitignore` 隔离敏感文件、分级日志、自定义分页组件、统一表单样式混入类。

### 12.2 答辩演示顺序建议

1. 未登录访问内页 → 演示登录拦截
2. admin 登录 → 看菜单最全、首页图表
3. 部门新增 → 删除有员工的部门（演示保护）
4. 员工列表 → 上传头像 → 切换 manager01 看数据范围收窄
5. 考勤录入 09:30 → 状态自动变"迟到"
6. 薪资录入 → 实发自动计算
7. 公告置顶 → 任务 AJAX 提交（强调页面不刷新）
8. 用户授权 → 给账号换角色 → 侧边栏实时变化
9. AI 悬浮球 → 问"张伟的考勤" → 展示数据感知能力
10. AI 知识库 → 问请假流程 → 展示命中条目

### 12.3 可扩展方向

- 考勤增加请假审批流程与状态机
- 薪资增加批量导入与个税计算
- 公告增加附件上传与已读回执
- AI 增加流式输出（SSE）替代前端模拟打字
- 接入缓存（Redis）优化图表统计接口

---

## 十三、安全说明

- `.env`、`media/`、`logs/`、`__pycache__/`、`.idea/` 均已写入 `.gitignore`
- API Key 只从环境变量读取，代码中没有任何硬编码密钥
- 密码使用 PBKDF2 哈希存储，数据库不保存明文
- 已开启 `X-Frame-Options: DENY`、`SECURE_CONTENT_TYPE_NOSNIFF`、`SESSION_COOKIE_HTTPONLY`
- 视图统一使用 ORM 参数化查询，避免 SQL 注入；模板默认转义，避免 XSS
- 表单统一做服务端校验，前端校验仅用于提升体验
