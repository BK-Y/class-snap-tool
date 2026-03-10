# 学员课堂表现速记系统

一个基于 Flask + SQLite 的课堂管理原型，当前重点覆盖学员信息管理与基础班级展示。

## 功能概览

- 学员列表查询（按姓名、昵称、性别筛选）
- 学员新增（常用称呼/法定姓名至少一项，法定姓名已可选）
- 班级模块基础入口
- SQLite 本地数据存储（首次运行自动建表）

## 项目结构

```text
class-snap-tool/
├── dao/                # 数据访问层
├── db/                 # 数据库连接与 schema
├── web/                # Flask 应用、路由与模板
├── run.py              # 跨平台统一启动入口（推荐）
├── requirements.txt
└── start.ps1           # Windows PowerShell 启动脚本
```

## 开发环境要求

- Python 3.10+
- pip
- Linux / Windows（均支持）


## 配置说明

系统配置通过环境变量驱动，应用启动时会从
`config.py` 读取设置。支持的变量包括：

* `SECRET_KEY` – Flask 会话密钥，生产环境**必须**设置。
* `DATABASE_PATH` – SQLite 数据文件路径（默认 `.data/school.db`）。
  也可指向其他数据库 URI。
* `HOST`, `PORT`, `DEBUG` – 与运行参数绑定。
* `FLASK_ENV` – 设为 `production` 时加载生产配置。

可在项目根创建 `.env` 文件并由 `python-dotenv` 加载，或者在
部署环境中直接设置变量。

> ⚠️ 切勿将敏感密钥硬编码在代码中。

## 安装与初始化

在项目根目录执行：

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## 启动方式（推荐）

统一命令（Win/Linux 相同）：

```bash
python run.py
```

可选参数：

```bash
python run.py --host 0.0.0.0 --port 5001 --debug
```

也支持环境变量：`HOST`、`PORT`、`DEBUG`。

启动后访问：<http://127.0.0.1:5000>

## 备选启动方式

```bash
python -m web.app
```

## 常见问题

### 1) 端口 5000 被占用

报错 `Address already in use` 时：

- 结束旧进程：`pkill -f "python -m web.app"`
- 或改端口：`python run.py --port 5001`

### 2) Linux 下没有 `Scripts` 目录

这是正常差异：

- Windows: `.venv/Scripts/`
- Linux/macOS: `.venv/bin/`

## 开发说明

- 入口文件：`run.py` / `web/app.py`
- 数据库 schema：`db/schema.sql`
- 首次启动会自动创建 `.data/school.db`

## 参与贡献

1. Fork 本仓库
2. 新建分支（如 `feat/xxx`）
3. 提交修改
4. 发起 Pull Request
