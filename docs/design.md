# 设计文档：课堂表现打分与排课方案

> **变更记录（Changelog）**
>
> - 2026-03-14：首次完成设计文档，包括三表（排课规则/课次/打分）建模、老师变更策略、典型查询示例。
> - 2026-03-15：实现三表模型（ClassSchedulePattern / ClassSession / SessionScore），完成 DAO 层和查询示例。
> - 2026-03-15：优化评分系统 UI，改为查看/编辑双模式，优化时间选择器。
> - **2026-03-15（最新）：重新设计评分系统数据库和 UI，采用更合理的评分记录模型。**
>
> 如果后续需求变更（如增加"课次补贴/教室管理"等），请在此处追加变更记录。

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
