-- 学生表
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,	 -- 系统内部id(技术主键)
    student_number TEXT NOT NULL UNIQUE,	-- 学号(业务id)
    display_name TEXT NOT NULL,				-- 常用称呼

    gender TEXT,				-- 性别
    gender_private BOOLEAN NOT NULL DEFAULT 0,				-- 是否选择公开


    -- 证件信息（法定，用于赛事报名等）
	legal_name TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    doc_number TEXT NOT NULL,

    -- 唯一约束
    UNIQUE (doc_type,doc_number) --证件名不重复
);

-- 班级表
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    level TEXT NOT NULL,
    group_number INTEGER NOT NULL,
    status TEXT DEFAULT 'active', UNIQUE(type, level, group_number)
);

-- 报名关系表
CREATE TABLE IF NOT EXISTS enrollments (
    student_id INTEGER,
    class_id INTEGER,
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, class_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- 课堂记录表
CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
