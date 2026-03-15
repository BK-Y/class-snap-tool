# 设计文档：课堂表现打分与排课方案

<details>
<summary><b>变更记录（点击展开）</b></summary>

- 2026-03-14
  1. 首次完成设计文档
  2. 三表（排课规则/课次/打分）建模
  3. 老师变更策略
  4. 典型查询示例

- 2026-03-15
  1. 实现三表模型（ClassSchedulePattern / ClassSession / SessionScore）
  2. 完成 DAO 层和查询示例
  3. 优化评分系统 UI，改为查看/编辑双模式
  4. 优化时间选择器（小时 8-22 点，分钟 10 分单位）
  5. 优化班级管理 UI，紧凑横向筛选工具栏
  6. 重构学员管理页面（渐变头部、学员徽章、日志弹窗）
  7. 完成计分模块完整需求梳理
     - 区分评分（学习报告）与奖励分（奖励币）
     - 作业评分规则（Z^分数）
     - 任务打分系统（完成形式/任务得分/协助他人/独立 T）
     - 常规表现（⭐）
     - 特殊表现记录（6+1 类型 + 备注）
  8. 补充后续开发规划
     - 学员学习报告系统
     - 教案管理系统
     - 机械建模模块
     - 图形化编程模块
     - 账号体系
     - 家长端
     - 微信接入

</details>

如果后续需求变更（如增加"课次补贴/教室管理"等），请在此处追加变更记录。

## 当前进展（基于现有代码/数据库）

### ✅ 已实现

**数据模型**：
- `students` / `student_documents`（学员与多证件支持）
- `classes`（班级基本信息，包括班级类型/级别/期数，及老师/上课时间描述）
- `enrollments` + `enrollment_logs`（学员报名关系与历史审计）
- `learning_records`（课堂表现/考勤/作业等记录的通用存储）
- `student_operation_logs`（学员信息变更审计）
- **`class_schedule_patterns`**（排课规则表）
- **`class_sessions`**（实际课次表）
- **`session_scores`**（打分明细表）
- **`class_schedule_pattern_history`**（排课规则修改历史表）

**DAO 层**：
- `dao/student_sa_dao.py` - 学员 CRUD
- `dao/class_sa_dao.py` - 班级管理
- `dao/enrollment_sa_dao.py` - 班级 - 学员关联
- **`dao/session_dao.py`** - 排课规则/课次/打分 CRUD + 统计函数
- **`dao/session_query_examples.py`** - 典型查询示例（设计文档中的查询场景）

**Web 功能**：
- 学员列表查询与筛选（姓名/昵称/性别/班级）
- 学员新增/编辑流程（支持多个证件，主证件标记）
- 班级基础入口与报名关系管理
- 学员操作日志记录（新增/修改/删除）
- **课次管理**（添加课次、标记完成/取消、删除）
- **排课规则管理**（添加/编辑/删除，带历史记录）
- **评分查看/编辑**（查看模式 + 编辑模式切换）
- **班级筛选**（按老师/周几/类型/状态筛选）

### ⏳ 待实现/待优化

- 课次生成与管理（按排课规则自动生成课次）
- 打分统计报表（出勤率、分数趋势、学员排名）
- 停课/补课/改期流程
- 移动端 UI 优化

### 📋 待验证（设计方案阶段）

- **评分系统重新设计**（见下方"评分系统重新设计方案"）
  - 当前评分表设计存在数据冗余、UI 交互差、缺少上下文等问题
  - 拟采用"批次 + 项目"两层结构，支持一节课多次评分
  - 需验证：数据迁移方案、UI 交互流程、性能表现

本项目的核心目标之一是构建一套可持续、可扩展的“课堂表现打分系统”，并支持排课、停课与补课等真实业务场景。

## 核心需求

- **以“节次/课次”为单位**记录课堂表现（每节课单元独立）。
- **打分项目可多次评分**（同一节课的不同阶段/环节）。
- **打分内容包括**：
  - 出勤（Q）：5 全勤，0 缺勤，3 补课
  - 当小老师（T）：每次出现计次，可表现为 +1
  - 创新方案（C）
  - 任务推荐（M1、M2）：每个子任务单独评分
  - 常规表现（N）
- 每条打分记录可包含**文字描述**（老师补充当堂表现/情境）。
- 可按**学年/学期/学员/班级**进行汇总与统计。
- 以**手机/平板操作为目标**，录入流程要尽量简单。

## 数据模型（推荐三表结构）

为保障核心需求，我们采用三张表分别表示：

1. **排课规则（schedule patterns）**
2. **实际课次（sessions）**
3. **打分明细（scores）**

### 1) `class_schedule_patterns`（课程排布规则）

用于描述“这门课通常什么时候上”，支持周期性排课（例如每周六 10:00-12:00）及有效期。

字段参考：

- `id`（主键）
- `class_id`（外键 → `classes.id`，必需）
- `weekday`（0-6 或 Mon-Sun）
- `start_time` / `end_time`（如 `10:00` / `12:00`）
- `repeat_interval`（每几周一次，默认 1）
- `valid_from` / `valid_to`（有效区间，用于学期/档期）
- `note`（备注，如“寒假停课”）

> 这张表用于生成“本学期预计上课安排”，并作为显示排课规则的依据。

### 2) `class_sessions`（实际课次）

表示“某门课在某天实际上发生的课次”，支持停课/补课/改期等状态。

关键字段建议：

- `id`（主键）
- `class_id`（外键 → `classes.id`，必需）
- `schedule_pattern_id`（可选外键 → `class_schedule_patterns.id`，关联来源规则）
- `session_date`（上课日期）
- `start_time` / `end_time`（可选：临时改时间）
- `session_index`（第几次课，可选）
- `session_stage`（环节/阶段，可选，如“讲解/实操/汇报”）
- `status`（枚举：`scheduled`/`held`/`canceled`/`rescheduled`）
- `cancel_reason`（停课原因，如“教师请假”）
- `reschedule_to_session_id`（可选：改期时关联的新课次）
- `is_extra`（是否补课/临时加课）
- `topic` / `summary`（本节课核心内容/主题）
- `teacher` / `teacher_id`（可选：实际上课老师，覆盖班级默认老师）
- `created_at`（记录创建时间）

> 这张表记录“实际发生了哪些课”，以及“为什么停/补/改”、”这节课是什么内容“。

#### 老师变更策略（推荐）

- **班级默认老师**：存于 `classes.teacher`（表示该班级长期负责老师）。
- **课次实际老师**：存于 `class_sessions.teacher`（记录该次谁上课，支持代课/请假情况）。
- 展示时：优先使用 `class_sessions.teacher`，若为空则回退到班级默认老师。

这个策略确保：
- 老师离职/变更不会影响历史课次和已打分数据。
- 临时代课/请假能精确记录。

### 3) `session_scores`（打分明细表）

表示老师对某节课中某位学生的一次“打分动作”，同一项目可多次打分（不同阶段）。

字段参考：

- `id`（主键）
- `session_id`（外键 → `class_sessions.id`，必需）
- `student_id`（外键 → `students.id`，必需）
- `score_type`（打分类别：Q/T/C/M1/M2/N）
- `score`（分数，0~5，0 表示缺勤）
- `comment`（描述/补充说明，如“发言+1”/“任务完成”）
- `recorded_by`（记录人，可由老师手动填写或使用默认标识）
- `created_at`（打分时间）

## 查询示例（组合视图）

- **某学员的全部上课记录**：从 `session_scores` 过滤 `student_id`，联表 `class_sessions`（过滤 `status=held`）和 `classes`，即可获得“在哪些班级、哪些节课、打了哪些分”。
- **某班级的排课与实际课次对比**：通过 `class_schedule_patterns`（预期安排）与 `class_sessions`（实际发生/取消/补课）关联。

## 为什么采用三表而不是两表

三表结构的优势在于：

- **规则与事实分离**：排课规则（周期/学期）可以独立存储，变更时不会影响已生成的课次与历史打分。
- **历史可追溯**：排课规则调整时，通过新增/失效规则而非改动旧记录，避免破坏历史数据。
- **查询更明确**：
  - 规则表负责“这门课通常怎么排”
  - 课次表负责“实际发生了哪些课/停课了哪些课”
  - 打分表负责“某节课某个学生的评分细节”
- **支持复杂场景**：如停课后补课、临时调整时间、代课等，都可以通过课次状态与关联字段表达。

## 实施建议步骤

1. 设计/扩展数据库模型（新增排课规则/课次/打分表）
2. 实现 DAO 层（CRUD + 统计）
3. 加入视图路由与模板（课次列表、打分页面、统计报表）
4. 优化移动端 UI，确保老师能“随手打分”。

## 评分系统重新设计方案（最新）

### 问题分析

当前 `session_scores` 表设计存在以下问题：

1. **一条记录一个分数** - 每个学生的每个打分项目需要一条独立记录，导致：
   - 数据冗余（同一 session 的多个学生重复存储 session_id）
   - 查询复杂（需要多次 JOIN 才能获取完整评分）
   - 编辑困难（修改时需要删除重建或逐条更新）

2. **UI 交互不合理** - 当前表格形式的问题：
   - 横向列太多（7 列分数 + 备注），移动端无法显示
   - 每次查看所有学生的所有分数，数据量大时加载慢
   - 编辑模式需要遍历所有学生的所有分数项

3. **缺少评分上下文** - 无法记录：
   - 评分的具体时间（一节课可能 120 分钟，何时打的分数？）
   - 评分的环节（讲解环节/实操环节/总结环节？）
   - 评分的权重（某些环节可能更重要）

### 新设计方案

#### 方案 A：评分项独立表（推荐）

**核心思路**：将"评分项"作为独立实体，支持一节课多次评分，每次评分可包含多个项目。

```sql
-- 评分批次表（记录何时何地何人评分）
CREATE TABLE session_score_batches (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,  -- 课次 ID
    scored_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 评分时间
    scored_by VARCHAR(32) NOT NULL,  -- 评分人
    stage VARCHAR(32),  -- 环节（讲解/实操/总结）
    note TEXT,  -- 本次评分的备注
    FOREIGN KEY(session_id) REFERENCES class_sessions(id)
);

-- 评分明细表（每个学生的具体分数）
CREATE TABLE session_score_items (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL,  -- 所属评分批次
    student_id INTEGER NOT NULL,  -- 学员 ID
    score_type VARCHAR(8) NOT NULL,  -- Q/T/C/M1/M2/N
    score FLOAT,  -- 分数
    comment TEXT,  -- 该项的备注
    FOREIGN KEY(batch_id) REFERENCES session_score_batches(id),
    FOREIGN KEY(student_id) REFERENCES students(id)
);
```

**优点**：
- 支持一节课多次评分（不同时间段/不同环节）
- 评分批次记录上下文（时间、环节、评分人）
- 查询灵活（可按批次查询，也可按学生汇总）
- 扩展性强（未来可添加评分维度、权重等）

**缺点**：
- 需要两张表，查询略复杂
- 历史数据迁移需要脚本

#### 方案 B：JSON 存储（简化版）

**核心思路**：将每个学生的所有分数存储为 JSON，减少表连接。

```sql
CREATE TABLE session_scores_v2 (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    scores JSON NOT NULL,  -- {"Q": 5, "T": 1, "C": 2, "M1": 4, "M2": 3, "N": 4}
    comment TEXT,
    recorded_by VARCHAR(32),
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES class_sessions(id),
    FOREIGN KEY(student_id) REFERENCES students(id),
    UNIQUE(session_id, student_id)
);
```

**优点**：
- 单表存储，查询简单
- 每个学生一条记录，数据量小
- 编辑方便（更新 JSON 即可）

**缺点**：
- SQLite 的 JSON 支持有限（查询/统计不便）
- 无法记录评分时间和环节
- 违反第一范式（后续扩展受限）

### 推荐实施方案 A

#### 第一步：创建新表

```python
class SessionScoreBatch(db.Model):
    __tablename__ = 'session_score_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'), nullable=False)
    scored_at = db.Column(db.DateTime, default=db.func.now())
    scored_by = db.Column(db.String(32), nullable=False)
    stage = db.Column(db.String(32))  # 讲解/实操/总结
    note = db.Column(db.Text)
    
    session = db.relationship('ClassSession', backref='score_batches')
    items = db.relationship('SessionScoreItem', backref='batch', cascade='all, delete-orphan')


class SessionScoreItem(db.Model):
    __tablename__ = 'session_score_items'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('session_score_batches.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    score_type = db.Column(db.String(8), nullable=False)
    score = db.Column(db.Float)
    comment = db.Column(db.Text)
    
    student = db.relationship('Student', backref='score_items')
```

#### 第二步：UI 交互设计

**查看模式**：
```
┌────────────────────────────────────────────────────┐
│  课次：2026-03-15 第 1 次课                        │
├────────────────────────────────────────────────────┤
│  评分记录 1 [2026-03-15 10:30 讲解环节]  张老师    │
│  ┌─────────┬────┬────┬────┬────┬────┬──────────┐ │
│  │ 学员    │ Q  │ T  │ C  │ M1 │ M2 │ 备注     │ │
│  ├─────────┼────┼────┼────┼────┼────┼──────────┤ │
│  │ 张三    │ 5  │ 1  │ -  │ 4  │ -  │ 表现积极 │ │
│  │ 李四    │ 5  │ -  │ 2  │ 5  │ -  │ 创新突出 │ │
│  └─────────┴────┴────┴────┴────┴────┴──────────┘ │
│                                                    │
│  评分记录 2 [2026-03-15 11:30 实操环节] 张老师    │
│  ┌─────────┬────┬────┬────┬────┬────┬──────────┐ │
│  │ 学员    │ Q  │ T  │ C  │ M1 │ M2 │ 备注     │ │
│  ├─────────┼────┼────┼────┼────┼────┼──────────┤ │
│  │ 张三    │ -  │ 1  │ -  │ -  │ 5  │ 完成很好 │ │
│  └─────────┴────┴────┴────┴────┴────┴──────────┘ │
│                                                    │
│  [+ 添加评分记录]                                  │
└────────────────────────────────────────────────────┘
```

**编辑模式**：
- 点击「添加评分记录」弹出表单
- 选择环节（讲解/实操/总结）
- 自动加载该课次的所有学员列表
- 每个学员一行，每项分数用下拉框选择
- 底部统一备注框
- 保存后创建一个新的评分批次

#### 第三步：迁移现有数据

```python
def migrate_old_scores():
    # 将旧的 session_scores 迁移到新的 batch + items 结构
    old_scores = SessionScore.query.all()
    
    # 按 session_id 分组
    from collections import defaultdict
    grouped = defaultdict(list)
    for s in old_scores:
        grouped[s.session_id].append(s)
    
    # 为每个 session 创建一个批次
    for session_id, scores in grouped.items():
        batch = SessionScoreBatch(
            session_id=session_id,
            scored_at=scores[0].created_at,
            scored_by=scores[0].recorded_by,
            note='迁移自旧版评分数据'
        )
        db.session.add(batch)
        db.session.flush()
        
        for s in scores:
            item = SessionScoreItem(
                batch_id=batch.id,
                student_id=s.student_id,
                score_type=s.score_type,
                score=s.score,
                comment=s.comment
            )
            db.session.add(item)
    
    db.session.commit()
```

### 实施步骤

1. **创建新模型和迁移脚本**
2. **实现新的 DAO 层函数**
   - `create_score_batch()` - 创建评分批次
   - `add_score_items()` - 添加评分项
   - `list_score_batches_for_session()` - 获取课次的所有评分批次
   - `get_student_scores_summary()` - 汇总学生所有分数
3. **更新前端 UI**
   - 按批次显示评分
   - 添加评分批次表单
   - 支持编辑/删除批次
4. **数据迁移**
   - 编写迁移脚本
   - 保留旧表作为备份
   - 验证数据完整性
5. **测试验证**
   - 单元测试 DAO 函数
   - 集成测试 UI 流程
   - 性能测试（大数据量场景）

### 对比总结

| 特性 | 当前设计 | 新设计（方案 A） |
|------|----------|-----------------|
| 数据结构 | 单表扁平存储 | 批次 + 项目两层 |
| 评分次数 | 每生每课一次 | 每生每课多次 |
| 时间记录 | 仅创建时间 | 每次评分时间 |
| 环节记录 | ❌ 不支持 | ✅ 支持 |
| 查询效率 | 需多次 JOIN | 按批次查询 |
| 编辑便利 | 需逐条更新 | 整批更新 |
| 扩展性 | 受限 | 强（可加权重等） |
| 移动端适配 | ❌ 列太多 | ✅ 分批显示 |

---

## 计分模块完整需求（最新）

### 一、核心概念区分

| 类型 | 用途 | 计入奖励币 | 记录时机 |
|------|------|------------|----------|
| **评分** | 生成学习报告 | ❌ 不计入 | 课中记录 |
| **奖励分** | 核算奖励币 | ✅ 计入 | 课中记录 |

### 二、打分项目分类

```
每节课打分
├── 基础打分（作业）
│   └── Z^分数（奖励分，计入奖励币）
│
├── 任务打分（M 系列）
│   ├── 完成形式评分（1-4 分，用于学习报告）
│   ├── 任务得分（奖励分，计入奖励币）
│   ├── 协助他人 T（奖励分）
│   └── 独立 T（奖励分）
│
├── 常规表现（⭐）
│   └── 积极发言等（奖励分）
│
└── 特殊表现记录
    └── 批判性思维/创新/协作等（记录，不计入奖励币）
```

### 三、作业评分（Z）

#### 评分规则
| 状态 | 奖励分 | 说明 |
|------|--------|------|
| 做了 | 老师输入（通常 +2） | 群里提交了作业 |
| 报备 | 0 | 提前报备太难，老师许可 |
| 没做 | 老师输入（通常 -1） | 无任何提交 |

**显示格式**：`Z^2`、`Z^0`、`Z^(-1)`

#### 数据模型
```python
class HomeworkRecord(db.Model):
    __tablename__ = 'homework_records'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    
    points = db.Column(db.Integer, default=0)  # 可为正/负/零
    teacher_note = db.Column(db.String(256))  # 老师备注
    
    recorded_by = db.Column(db.String(32))
    recorded_at = db.Column(db.DateTime, default=db.func.now())
```

### 四、任务打分（M 系列）

#### 4.1 任务添加
- 点击 [+ 添加任务] 按钮
- 系统自动编号（M1/M2/M3...）
- 无需手动输入编号

#### 4.2 完成形式评分（用于学习报告）
| 选项 | 分数 | 默认 |
|------|------|------|
| 完全自己独立完成 | 4 分 | ○ |
| 老师指导完成 | 3 分 | ● |
| 老师带着完成 | 2 分 | ○ |
| 未完成 | 1 分 | ○ |

#### 4.3 任务得分（奖励分）
| 操作 | 奖励分 | 说明 |
|------|--------|------|
| 点击"完成"按钮 | +1 分 | 按钮消失，显示"已完成" |
| 点击分数按钮 | +N 分 | 弹出输入框，输入额外奖励分 |
| 未完成 | 0 分 | 默认状态 |

**备注**：独立完成的学生，任务得分会有额外体现（用于后续分析）

#### 4.4 协助他人（T）
- 每成功帮助 1 人 → +1 分
- 输入帮助人数，自动计算奖励分

#### 4.5 独立 T
- 非任务环节分享知识（如当小老师讲课）
- 直接输入奖励分

#### 4.6 显示格式
```
M1^2 T^1
└─ 任务得 2 分  └─ T 奖励 1 分（协助 + 独立）
```

#### 4.7 数据模型
```python
class TaskDefinition(db.Model):
    __tablename__ = 'task_definitions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'))
    task_code = db.Column(db.String(8), nullable=False)  # 'M1', 'M2'...
    task_number = db.Column(db.Integer, nullable=False)  # 1, 2...
    difficulty = db.Column(db.Float, default=1.0)  # 课后修改


class TaskScore(db.Model):
    __tablename__ = 'task_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task_definitions.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    
    # 评分（用于学习报告）
    completion_rating = db.Column(db.Integer, default=3)  # 1/2/3/4
    
    # 奖励分（计入奖励币）
    task_points = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    helped_count = db.Column(db.Integer, default=0)
    help_points = db.Column(db.Integer, default=0)
    independent_t = db.Column(db.Integer, default=0)
    bonus_points = db.Column(db.Integer)  # 自动计算
    
    recorded_at = db.Column(db.DateTime, default=db.func.now())
    recorded_by = db.Column(db.String(32))
```

### 五、常规表现（⭐）

| 情况 | 奖励分 |
|------|--------|
| 积极发言 | +1 |
| 好行为 | +1 |
| 其他 | 老师输入 |

**显示格式**：`⭐^2`（表示 2 次积极发言）

### 六、特殊表现记录

#### 6.1 表现类型
| 类型 | 图标 | 说明 |
|------|------|------|
| 🧠 批判性思维 | `critical_thinking` | 提出质疑、多角度思考 |
| 💡 创新 | `innovation` | 独特解法、创意想法 |
| 🤝 协作 | `collaboration` | 主动帮助、团队合作 |
| 📈 明显进步 | `progress` | 相比之前有明显提升 |
| 🎯 领导力 | `leadership` | 组织、带领他人 |
| 💪 坚持 | `persistence` | 面对困难不放弃 |
| 🌟 其他 | `other` | 老师自定义 |

#### 6.2 UI 操作
- 每个学生姓名旁有 [🌟+] 按钮
- 点击弹出特殊表现记录弹窗
- 选择类型 → 填写描述 → 保存

#### 6.3 电脑端显示
- 学生姓名后显示特殊表现图标（💡📈）
- 鼠标悬停显示具体内容
- 下方"特殊表现"区域显示完整记录

#### 6.4 数据模型
```python
class SpecialAchievement(db.Model):
    __tablename__ = 'special_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    
    achievement_type = db.Column(db.String(16), nullable=False)
    description = db.Column(db.Text, nullable=False)
    related_task_id = db.Column(db.Integer, db.ForeignKey('task_definitions.id'))
    
    # 备注（老师内部备注，不显示给学生/家长）
    teacher_note = db.Column(db.Text)
    
    recorded_by = db.Column(db.String(32))
    recorded_at = db.Column(db.DateTime, default=db.func.now())
```

### 七、奖励币核算规则

```
奖励币 = 作业奖励分 + 任务奖励分 + 常规奖励分

其中：
- 作业奖励分 = Σ(Z^分数)
- 任务奖励分 = Σ(任务得分 + 协助他人分 + 独立 T 分)
- 常规奖励分 = Σ(⭐分数)
```

### 八、后台功能

#### 8.1 任务难度批量修改
```
课次管理 → 任务难度批量修改

M1  难度：[1.0 ▼]  [保存]
M2  难度：[1.5 ▼]  [保存]
M3  难度：[2.0 ▼]  [保存]

[全部保存]
```

### 九、后续开发计划

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 学习报告生成 | 期末基于完成形式评分生成报告 | P2 |
| 任务难度分析 | 基于难度系数和学生完成情况分析 | P2 |
| 独立完成分析 | 基于备注识别独立完成的学生 | P2 |
| 奖励币排行榜 | 按奖励币数量排名 | P1 |
| 导出 Excel | 导出评分记录 | P1 |
| 特殊表现统计 | 按类型统计，生成学生亮点报告 | P2 |

### 十、实施优先级

| 优先级 | 模块 | 说明 |
|--------|------|------|
| **P0** | 作业评分 | Z^分数 |
| **P0** | 任务添加 | 自动编号 |
| **P0** | 任务打分 | 完成按钮 + 奖励分输入 |
| **P0** | 完成形式评分 | 1-4 分，默认 3 分 |
| **P0** | 实时同步 | 手机打分，电脑显示 |
| **P1** | 协助他人 | 每帮助 1 人 +1 分 |
| **P1** | 独立 T | 非任务环节分享 |
| **P1** | 常规奖励 | ⭐ |
| **P1** | 特殊表现记录 | 6+1 类型 + 备注 |
| **P1** | 奖励币核算 | 所有奖励分累加 |
| **P2** | 任务难度批量修改 | 课后后台修改 |
| **P2** | 学习报告 | 期末生成 |
| **P2** | 特殊表现统计 | 按类型统计 |

---

## 附录：快速参考

### 显示格式速查
| 类型 | 格式 | 示例 |
|------|------|------|
| 作业 | Z^分数 | Z^2, Z^0, Z^(-1) |
| 任务 | M 编号^分数 T^T 分 | M1^2 T^1 |
| 常规 | ⭐^分数 | ⭐^2 |
| 特殊表现 | 图标 + 描述 | 💡 创新："提出独特解法" |

### 评分 vs 奖励分速查
| 项目 | 评分（学习报告） | 奖励分（奖励币） |
|------|-----------------|-----------------|
| 作业 | ❌ | ✅ Z^分数 |
| 任务完成形式 | ✅ 1-4 分 | ❌ |
| 任务得分 | ❌ | ✅ 完成 1 分 + 额外奖励 |
| 协助他人 | ❌ | ✅ +1 分/人 |
| 独立 T | ❌ | ✅ 老师输入 |
| 常规表现 | ❌ | ✅ ⭐^分数 |
| 特殊表现 | ✅ 记录 | ❌ |

---

## 后续开发规划

### 一、学员学习报告系统

#### 1.1 报告内容
```
学员学习报告
├── 基本信息
│   ├── 学员姓名
│   ├── 班级
│   └── 报告周期（如 2026 年春季学期）
│
├── 出勤统计
│   ├── 总课次
│   ├── 全勤次数
│   ├── 缺勤次数
│   ├── 补课次数
│   └── 出勤率
│
├── 任务完成情况
│   ├── 完成任务总数
│   ├── 独立完成次数
│   ├── 指导完成次数
│   ├── 未完成次数
│   └── 独立完成率
│
├── 特殊表现统计
│   ├── 🧠 批判性思维：X 次
│   ├── 💡 创新：X 次
│   ├── 🤝 协作：X 次
│   ├── 📈 明显进步：X 次
│   ├── 🎯 领导力：X 次
│   ├── 💪 坚持：X 次
│   └── 典型案例分析
│
├── 奖励币统计
│   ├── 作业奖励：X 分
│   ├── 任务奖励：X 分
│   ├── 常规表现：X 分
│   ├── 特殊表现：X 分（可选）
│   └── 总计：X 分
│
├── 能力雷达图
│   ├── 动手能力
│   ├── 逻辑思维
│   ├── 创新思维
│   ├── 团队协作
│   └── 表达能力
│
└── 老师评语
    ├── 优势
    ├── 待提升
    └── 建议
```

#### 1.2 报告生成方式
| 方式 | 说明 | 优先级 |
|------|------|--------|
| 期末统一生成 | 基于整学期数据自动生成 | P1 |
| 月度简报 | 每月生成简化版报告 | P2 |
| 课后小结 | 每节课后生成简单总结 | P3 |
| 自定义生成 | 老师手动选择周期生成 | P2 |

#### 1.3 报告输出形式
- PDF 下载（可打印）
- H5 页面（手机查看）
- 微信推送（家长端）

---

### 二、教案管理系统

#### 2.1 核心功能
| 功能 | 说明 | 优先级 |
|------|------|--------|
| 教案编写 | 支持图文混排、代码块 | P1 |
| 教案模板 | 预设常用教案模板 | P1 |
| 教案库 | 按课程/难度/主题分类 | P1 |
| 教案共享 | 老师之间共享教案 | P2 |
| 版本管理 | 教案修改历史记录 | P2 |
| 教案关联 | 关联任务、评分标准 | P2 |

#### 2.2 教案结构
```
教案
├── 基本信息
│   ├── 课程名称
│   ├── 适用班级
│   ├── 课时
│   └── 难度等级
│
├── 教学目标
│   ├── 知识目标
│   ├── 能力目标
│   └── 素养目标
│
├── 教学重难点
│   ├── 重点
│   └── 难点
│
├── 教学准备
│   ├── 硬件清单
│   ├── 软件/程序
│   └── 教学资源
│
├── 教学过程
│   ├── 导入（5 分钟）
│   ├── 讲解（15 分钟）
│   ├── 实践（60 分钟）
│   ├── 展示（15 分钟）
│   └── 总结（5 分钟）
│
├── 任务设计
│   ├── M1 基础任务
│   ├── M2 进阶任务
│   └── M3 挑战任务
│
├── 评分标准
│   ├── 完成形式评分标准
│   ├── 任务得分标准
│   └── 特殊表现观察点
│
└── 教学反思
    ├── 成功之处
    ├── 不足之处
    └── 改进建议
```

#### 2.3 数据模型（简略）
```python
class LessonPlan(db.Model):
    __tablename__ = 'lesson_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))  # 教案标题
    course_id = db.Column(db.Integer)  # 关联课程
    difficulty = db.Column(db.String(8))  # 难度
    duration = db.Column(db.Integer)  # 课时（分钟）
    
    content = db.Column(db.Text)  # 教案内容（Markdown/HTML）
    tasks = db.Column(db.JSON)  # 任务设计
    rubric = db.Column(db.JSON)  # 评分标准
    
    created_by = db.Column(db.String(32))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
```

---

### 三、机械建模模块

#### 3.1 功能定位
- 学生设计机械结构的工具
- 支持 3D 模型查看和编辑
- 与任务系统关联（完成任务需要提交模型）

#### 3.2 核心功能
| 功能 | 说明 | 优先级 |
|------|------|--------|
| 模型库 | 预设常用零件模型 | P1 |
| 拖拽建模 | 拖拽零件组装机械结构 | P1 |
| 3D 查看 | 旋转、缩放、剖视 | P1 |
| 模型保存 | 保存学生作品 | P1 |
| 模型分享 | 分享到班级/全校 | P2 |
| 模型评审 | 老师点评、打分 | P2 |
| 动画仿真 | 模拟机械运动 | P3 |

#### 3.3 技术选型
| 方案 | 优点 | 缺点 |
|------|------|------|
| WebGL (Three.js) | 跨平台，无需安装 | 性能有限 |
| Unity WebGL | 功能强大，效果好 | 包体积大 |
| 本地客户端 | 性能最好 | 需安装 |

**推荐**：WebGL (Three.js) - 跨平台、易部署

---

### 四、图形化编程模块

#### 4.1 功能定位
- 学生编写程序的工具
- 基于 Scratch/Blockly
- 与任务系统关联（完成任务需要提交程序）

#### 4.2 核心功能
| 功能 | 说明 | 优先级 |
|------|------|--------|
| 图形化编程 | 拖拽积木块编程 | P1 |
| 代码预览 | 查看生成的 Python/C 代码 | P1 |
| 程序运行 | 在线运行/仿真 | P2 |
| 程序保存 | 保存学生作品 | P1 |
| 程序分享 | 分享到班级/全校 | P2 |
| 程序评审 | 老师点评、打分 | P2 |
| 硬件下载 | 下载到真实硬件 | P3 |

#### 4.3 技术选型
| 方案 | 适用场景 | 优先级 |
|------|----------|--------|
| Scratch 3.0 | 低龄段，图形化 | P1 |
| Blockly | 自定义积木块 | P1 |
| MakeCode | 微控制器编程 | P2 |
| Python 编辑器 | 高龄段，代码编程 | P2 |

---

### 五、账号体系

#### 5.1 用户角色
| 角色 | 权限 | 优先级 |
|------|------|--------|
| 学生 | 查看自己的评分、作品、报告 | P1 |
| 老师 | 打分、管理班级、查看统计 | P1 |
| 家长 | 查看孩子的报告和表现 | P1 |
| 管理员 | 系统管理、用户管理 | P1 |
| 教研员 | 查看教案、统计分析 | P2 |

#### 5.2 登录方式
| 方式 | 说明 | 优先级 |
|------|------|--------|
| 账号密码 | 传统登录方式 | P1 |
| 手机验证码 | 短信验证码登录 | P1 |
| 微信扫码 | 微信快捷登录 | P1 |
| 钉钉 | 钉钉快捷登录 | P2 |
| SSO 单点登录 | 与学校系统集成 | P2 |

#### 5.3 数据模型（简略）
```python
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True)
    password_hash = db.Column(db.String(128))
    phone = db.Column(db.String(16))
    wechat_openid = db.Column(db.String(64))
    
    role = db.Column(db.String(16))  # student/teacher/parent/admin
    real_name = db.Column(db.String(32))
    
    created_at = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
```

---

### 六、家长端

#### 6.1 功能定位
- 家长查看孩子学习情况的入口
- 以微信小程序为主
- 推送通知、报告

#### 6.2 核心功能
| 功能 | 说明 | 优先级 |
|------|------|--------|
| 课表查看 | 查看孩子的课程安排 | P1 |
| 评分查看 | 查看每次课的评分 | P1 |
| 报告查看 | 查看学习报告 | P1 |
| 作品查看 | 查看孩子的机械/编程作品 | P1 |
| 消息通知 | 上课提醒、作业提醒 | P1 |
| 请假功能 | 在线请假 | P1 |
| 与老师沟通 | 私信老师 | P2 |
| 家长社区 | 家长之间交流 | P3 |

#### 6.3 技术选型
| 方案 | 优点 | 缺点 |
|------|------|------|
| 微信小程序 | 无需安装，易传播 | 功能受限 |
| 微信公众号 | 推送方便 | 交互受限 |
| 独立 App | 功能完整 | 需安装 |

**推荐**：微信小程序（主）+ 微信公众号（推送）

---

### 七、微信接入

#### 7.1 接入方式
| 方式 | 说明 | 优先级 |
|------|------|--------|
| 微信公众号 | 服务号，推送通知 | P1 |
| 微信小程序 | 家长端、学生端 | P1 |
| 企业微信 | 老师端、内部沟通 | P2 |
| 微信支付 | 缴费、购买奖励 | P3 |

#### 7.2 推送内容
| 类型 | 触发时机 | 优先级 |
|------|----------|--------|
| 上课提醒 | 课前 1 小时 | P1 |
| 作业提醒 | 课后/截止前 | P1 |
| 评分通知 | 课后实时 | P1 |
| 报告生成 | 期末/月度 | P1 |
| 特殊表现 | 记录后实时 | P2 |
| 活动通知 | 比赛/活动 | P2 |

#### 7.3 技术实现
```python
# 微信推送服务
class WeChatService:
    def send_template_message(self, openid, template_id, data):
        """发送模板消息"""
        pass
    
    def send_subscription_message(self, openid, template_id, data):
        """发送订阅消息"""
        pass
    
    def create_qrcode(self, scene_id):
        """生成带参二维码"""
        pass
```

---

### 八、整体架构规划

#### 8.1 系统模块
```
学员课堂表现速记系统
├── 核心模块（已实现/规划中）
│   ├── 学员管理 ✅
│   ├── 班级管理 ✅
│   ├── 课次管理 ✅
│   ├── 评分系统 ✅
│   └── 特殊表现记录 ✅
│
├── 后续开发模块
│   ├── 学员报告系统 📋
│   ├── 教案管理系统 📋
│   ├── 机械建模模块 📋
│   ├── 图形化编程模块 📋
│   ├── 账号体系 📋
│   ├── 家长端 📋
│   └── 微信接入 📋
│
└── 支撑系统
    ├── 数据统计与分析
    ├── 文件存储（模型/程序）
    └── 消息推送
```

#### 8.2 开发优先级
| 阶段 | 模块 | 说明 |
|------|------|------|
| **第一阶段** | 评分系统 | 当前已完成需求梳理 |
| **第二阶段** | 账号体系 + 微信接入 | 基础支撑系统 |
| **第三阶段** | 家长端 | 微信小程序 |
| **第四阶段** | 学员报告系统 | 基于已有数据生成报告 |
| **第五阶段** | 教案管理系统 | 老师备课工具 |
| **第六阶段** | 机械建模 + 图形化编程 | 学生创作工具 |

---

## 总结

本文档涵盖了：
1. ✅ 排课规则与课次管理
2. ✅ 评分系统（作业/任务/常规/特殊表现）
3. ✅ 班级管理（学员/筛选/日志）
4. 📋 学员学习报告系统（规划）
5. 📋 教案管理系统（规划）
6. 📋 机械建模模块（规划）
7. 📋 图形化编程模块（规划）
8. 📋 账号体系（规划）
9. 📋 家长端（规划）
10. 📋 微信接入（规划）

**当前重点**：完成评分系统的开发实施（P0/P1 优先级功能）

**下一步**：账号体系 + 微信接入（为家长端和推送做准备）
