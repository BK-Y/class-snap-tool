
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    -- 系统内部id(技术主键)
    student_number TEXT NOT NULL UNIQUE,      -- 学号(业务id)
    display_name TEXT NOT NULL,               -- 常用称呼
    gender TEXT,                              -- 性别
    birthday TEXT,                            -- 生日
    birthday_cal TEXT,                        -- 生日所使用的日历,默认公历
    legal_name TEXT                          -- 证件信息（法定，用于赛事报名等，现为可选）
    -- 2026.03 多证件支持，主证件迁移至 student_documents 表
    -- doc_type TEXT NOT NULL,
    -- doc_number TEXT NOT NULL,
    -- UNIQUE (doc_type,doc_number) --证件名不重复
);

-- ============================================
-- 学生证件表 (student_documents)
-- 支持一个学生多个证件，且每个学生只能有一个主证件
-- ============================================
CREATE TABLE IF NOT EXISTS student_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    doc_number TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0, -- 1=主证件，0=非主证件
    UNIQUE (student_id, doc_type),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ============================================
-- 证件类型表（可扩展）
-- 默认包含身份证、港澳台通行证、护照、其他；
-- 用户新增类型会插入此表，便于下次使用。
-- ============================================
CREATE TABLE IF NOT EXISTS doc_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_code TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL
);
-- SQLite 不支持 UNIQUE ... WHERE 语法，主证件唯一性需用触发器或应用层保证
-- ============================================
-- 班级表 (classes)
-- 存储班级/课程信息
-- ============================================

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,         -- 班级 id
    type TEXT NOT NULL,                           -- 班级类型 (如：钢琴/舞蹈/绘画)
    level TEXT NOT NULL,                          -- 级别 (如：初级/中级/高级)
    group_number INTEGER NOT NULL,                -- 期数/班号 (如：第 1 期/第 2 期)
    status TEXT DEFAULT 'active',                 -- 班级状态 (active/inactive/completed)
    
    -- 唯一约束：同类型、同级别、同期数的班级不能重复
    UNIQUE(type, level, group_number)
);

-- ============================================
-- 报名关系表 (enrollments)
-- 存储学生与班级的报名关系 (多对多)
-- ============================================
CREATE TABLE IF NOT EXISTS enrollments (
    student_id INTEGER,                           -- 学生 id
    class_id INTEGER,                             -- 班级 id
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 报名时间
    
    -- 复合主键：同一学生同一班级只能报名一次
    PRIMARY KEY (student_id, class_id),
    
    -- 外键约束：学生或班级删除时，报名记录级联删除
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- ============================================
-- 报名事件日志表 (enrollment_logs)
-- 记录学员进出班级历史（用于审计与数据分析）
-- ============================================
CREATE TABLE IF NOT EXISTS enrollment_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,                     -- JOIN / LEAVE
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    operator_id TEXT NOT NULL,                    -- 谁操作
    reason TEXT,                                  -- 原因（可选）
    source TEXT DEFAULT 'web',                    -- 来源：web/import/api
    request_id TEXT,                              -- 请求追踪ID（可选）

    -- 快照字段（避免学员改名/改号后历史难读）
    student_number_snapshot TEXT,
    student_name_snapshot TEXT,

    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    CHECK (event_type IN ('JOIN', 'LEAVE'))
);

-- 报名日志常用索引
CREATE INDEX IF NOT EXISTS idx_enrollment_log_class_time ON enrollment_logs(class_id, event_time);
CREATE INDEX IF NOT EXISTS idx_enrollment_log_student_time ON enrollment_logs(student_id, event_time);
CREATE INDEX IF NOT EXISTS idx_enrollment_log_request_id ON enrollment_logs(request_id);

-- ============================================
-- 课堂记录表 (learning_records)
-- 存储学生的课堂表现、考勤、作业、考试等记录
-- ============================================
CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,         -- 记录 id
    
    student_id INTEGER NOT NULL,                  -- 哪个学生 (外键)
    class_id INTEGER NOT NULL,                    -- 哪个班级 (冗余存储，提升查询性能)
    academic_year TEXT NOT NULL,                  -- 学年 (如 '2023-2024')
    term TEXT,                                    -- 学期 (如 '春季'/'秋季'，可选)
    
    record_type TEXT NOT NULL DEFAULT 'general',  -- 记录类型：
                                                  --   'general'(一般记录)
                                                  --   'attendance'(考勤)
                                                  --   'performance'(课堂表现)
                                                  --   'homework'(作业)
                                                  --   'exam'(考试)
    content TEXT NOT NULL,                        -- 具体内容描述
    score REAL,                                   -- 分数/评级 (可选，用于量化表现，如 85.5 或 'A')
    
    recorded_by TEXT NOT NULL,                    -- 记录人 (老师 ID 或姓名)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间
    
    -- 外键约束：学生或班级删除时，记录级联删除
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);	

-- ============================================
-- 课堂记录表 - 索引设计
-- 目的：提升多维度查询性能
-- ============================================

-- 索引 1：快速查询某个学生的所有记录 (最常用)
-- 场景：打开学生详情页，查看该学生全部学习历史
CREATE INDEX IF NOT EXISTS idx_record_student ON learning_records(student_id);
-- 索引 2：快速查询某个学生某学年的记录
-- 场景：生成学生学年报告，如"张三 2023-2024 学年表现"
CREATE INDEX IF NOT EXISTS idx_record_student_year ON learning_records(student_id, academic_year);
-- 索引 3：快速查询某个班级某学年的记录
-- 场景：生成班级整体统计，如"钢琴初级 1 班 2023-2024 学年平均成绩"
CREATE INDEX IF NOT EXISTS idx_record_class_year ON learning_records(class_id, academic_year);

-- 索引 4：按时间排序查询
-- 场景：查看最新记录，或按时间线展示
CREATE INDEX IF NOT EXISTS idx_record_time ON learning_records(created_at);

-- 索引 5：复合索引 - 班级 + 学年 + 时间
-- 场景：生成班级学期报告，按时间顺序展示所有学生记录
CREATE INDEX IF NOT EXISTS idx_record_class_year_time ON learning_records(class_id, academic_year, created_at);

-- ============================================
-- 5. 学生操作日志表 (student_operation_logs)
-- 审计追踪：记录谁在什么时候修改了学生的什么信息
-- ============================================
CREATE TABLE IF NOT EXISTS student_operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,         -- 日志 id
    
    student_id INTEGER NOT NULL,                  -- 关联到哪个学生 (外键)
    operator_id TEXT NOT NULL,                    -- 谁操作的 (管理员 ID 或用户名)
    operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 操作时间
    
    operation_type TEXT NOT NULL,                 -- 操作类型：
                                                  --   'INSERT'(新增学员)
                                                  --   'UPDATE'(修改信息)
                                                  --   'DELETE'(删除学员)
    
    field_name TEXT,                              -- 修改了哪个字段 (如：'legal_name', 'birthday')
    old_value TEXT,                               -- 修改前的内容 (新增时为 NULL)
    new_value TEXT,                               -- 修改后的内容
    
    remark TEXT,                                   -- 备注 (可选，如"修正录入错误"、"家长要求修改")
    
    -- 外键约束：学生删除时，日志级联删除
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ============================================
-- 学生操作日志表 - 索引设计
-- 目的：提升审计查询性能
-- ============================================

-- 索引 1：快速查找某个学生的所有操作记录
-- 场景：查看"张三"的所有信息修改历史
CREATE INDEX IF NOT EXISTS idx_log_student_id ON student_operation_logs(student_id);

-- 索引 2：快速按时间筛选/排序
-- 场景：查看"最近 10 条操作"或"2024 年 1 月的所有修改"
CREATE INDEX IF NOT EXISTS idx_log_time ON student_operation_logs(operation_time);

-- ============================================
-- 设计说明总结
-- ============================================
-- 1. 范式遵循：
--    - 主表 (students/classes) 严格遵循第三范式 (3NF)
--    - learning_records 适度反范式化 (冗余 class_id) 换取查询性能
--
-- 2. 索引策略：
--    - 覆盖所有高频查询场景 (按学生、按班级、按学年、按时间)
--    - 复合索引优化多条件查询
--
-- 3. 数据完整性：
--    - 外键约束保证引用完整性
--    - UNIQUE 约束防止重复数据
--    - ON DELETE CASCADE 保证级联清理
--
-- 4. 审计追踪：
--    - 独立日志表记录所有学生信息变更
--    - 支持追溯"谁、何时、改了什么"
--
-- 5. 扩展性：
--    - record_type 支持新增记录类型
--    - score 支持量化评估
--    - 日志表支持未来扩展更多审计字段
-- ============================================