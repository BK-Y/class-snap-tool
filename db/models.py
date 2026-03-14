from db.sa_db import db


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(32), unique=True, nullable=False)
    display_name = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(8))
    birthday = db.Column(db.String(16))
    birthday_cal = db.Column(db.String(8))
    # 证件信息迁移到 student_documents
    documents = db.relationship('StudentDocument', backref='student', cascade="all, delete-orphan")


class StudentDocument(db.Model):
    __tablename__ = 'student_documents'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    doc_type = db.Column(db.String(32), nullable=False)
    doc_number = db.Column(db.String(64), nullable=False)
    # 新字段：证件上显示的姓名
    doc_name = db.Column(db.String(64), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'doc_type'),)


class DocType(db.Model):
    __tablename__ = 'doc_types'
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(32), unique=True, nullable=False)
    label = db.Column(db.String(32), nullable=False)


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(32), nullable=False)
    group_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(16), default='active')
    # additional metadata
    teacher = db.Column(db.String(64), nullable=True)
    class_time = db.Column(db.String(64), nullable=True)  # e.g. 周二 18:00-20:00
    start_date = db.Column(db.String(32), nullable=True)  # e.g. 2026-03-15
    __table_args__ = (db.UniqueConstraint('type', 'level', 'group_number'),)


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), primary_key=True)
    enrolled_at = db.Column(db.DateTime)


class EnrollmentLog(db.Model):
    __tablename__ = 'enrollment_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    event_type = db.Column(db.String(8), nullable=False)
    event_time = db.Column(db.DateTime)
    operator_id = db.Column(db.String(32), nullable=False)
    reason = db.Column(db.String(128))
    source = db.Column(db.String(16), default='web')
    request_id = db.Column(db.String(64))
    student_number_snapshot = db.Column(db.String(32))
    student_name_snapshot = db.Column(db.String(64))


class LearningRecord(db.Model):
    __tablename__ = 'learning_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    academic_year = db.Column(db.String(16), nullable=False)
    term = db.Column(db.String(8))
    record_type = db.Column(db.String(16), default='general')
    content = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float)
    recorded_by = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime)


class StudentOperationLog(db.Model):
    __tablename__ = 'student_operation_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    operator_id = db.Column(db.String(32), nullable=False)
    operation_time = db.Column(db.DateTime)
    operation_type = db.Column(db.String(8), nullable=False)
    field_name = db.Column(db.String(32))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    remark = db.Column(db.String(128))


# ==================== 三表模型：排课规则 / 课次 / 打分 ====================

class ClassSchedulePattern(db.Model):
    """排课规则表：描述班级通常的上课时间安排（周期性规则）"""
    __tablename__ = 'class_schedule_patterns'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)

    # 周期性排课字段
    weekday = db.Column(db.Integer, nullable=False, comment="星期几 (0=周一，6=周日)")
    start_time = db.Column(db.String(5), nullable=False, comment="开始时间 (HH:MM)")
    end_time = db.Column(db.String(5), nullable=False, comment="结束时间 (HH:MM)")
    repeat_interval = db.Column(db.Integer, default=1, comment="每几周一次，默认 1")

    # 有效期
    valid_from = db.Column(db.Date, nullable=True, comment="规则生效日期")
    valid_to = db.Column(db.Date, nullable=True, comment="规则失效日期")

    # 备注
    note = db.Column(db.String(128), nullable=True, comment="备注，如寒假停课")

    # 版本控制
    version = db.Column(db.Integer, default=1, comment="规则版本号")
    is_active = db.Column(db.Boolean, default=True, comment="是否当前有效")

    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # 关联
    class_ref = db.relationship('Class', backref=db.backref('schedule_patterns', cascade='all, delete-orphan'))
    history = db.relationship('ClassSchedulePatternHistory', backref='pattern', cascade='all, delete-orphan',
                              foreign_keys='ClassSchedulePatternHistory.pattern_id')

    __table_args__ = (
        db.CheckConstraint('weekday >= 0 AND weekday <= 6', 'check_weekday_range'),
        db.CheckConstraint('repeat_interval >= 1', 'check_repeat_interval_positive'),
    )


class ClassSchedulePatternHistory(db.Model):
    """排课规则修改历史表：记录每次规则变更，确保已发生课次不受影响"""
    __tablename__ = 'class_schedule_pattern_history'

    id = db.Column(db.Integer, primary_key=True)
    pattern_id = db.Column(db.Integer, db.ForeignKey('class_schedule_patterns.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)

    # 变更前的值（快照）
    old_weekday = db.Column(db.Integer, comment="原星期几")
    old_start_time = db.Column(db.String(5), comment="原开始时间")
    old_end_time = db.Column(db.String(5), comment="原结束时间")
    old_repeat_interval = db.Column(db.Integer, comment="原周期")
    old_valid_from = db.Column(db.Date, comment="原生效日期")
    old_valid_to = db.Column(db.Date, comment="原失效日期")
    old_note = db.Column(db.String(128), comment="原备注")

    # 变更后的值
    new_weekday = db.Column(db.Integer, comment="新星期几")
    new_start_time = db.Column(db.String(5), comment="新开始时间")
    new_end_time = db.Column(db.String(5), comment="新结束时间")
    new_repeat_interval = db.Column(db.Integer, comment="新周期")
    new_valid_from = db.Column(db.Date, comment="新生效日期")
    new_valid_to = db.Column(db.Date, comment="新失效日期")
    new_note = db.Column(db.String(128), comment="新备注")

    # 变更原因和操作人
    change_reason = db.Column(db.String(256), comment="变更原因")
    changed_by = db.Column(db.String(32), comment="操作人")
    changed_at = db.Column(db.DateTime, default=db.func.now(), comment="变更时间")

    # 影响评估
    affected_sessions_count = db.Column(db.Integer, default=0, comment="影响的未来课次数")

    __table_args__ = (
        db.Index('ix_history_pattern', 'pattern_id', 'changed_at'),
    )


class ClassSession(db.Model):
    """实际课次表：记录某门课在某天实际发生的课次（支持停课/补课/改期）"""
    __tablename__ = 'class_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    schedule_pattern_id = db.Column(db.Integer, db.ForeignKey('class_schedule_patterns.id'), nullable=True)
    
    # 课次基本信息
    session_date = db.Column(db.Date, nullable=False, comment="上课日期")
    start_time = db.Column(db.String(5), nullable=True, comment="实际开始时间 (HH:MM)")
    end_time = db.Column(db.String(5), nullable=True, comment="实际结束时间 (HH:MM)")
    session_index = db.Column(db.Integer, nullable=True, comment="第几次课")
    session_stage = db.Column(db.String(32), nullable=True, comment="环节/阶段，如讲解/实操/汇报")
    
    # 状态：scheduled/held/canceled/rescheduled
    status = db.Column(db.String(16), default='scheduled', nullable=False, comment="课次状态")
    
    # 停课/补课相关
    cancel_reason = db.Column(db.String(128), nullable=True, comment="停课原因")
    reschedule_to_session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'), nullable=True, comment="改期关联的新课次 ID")
    is_extra = db.Column(db.Boolean, default=False, comment="是否补课/临时加课")
    
    # 课程内容
    topic = db.Column(db.String(128), nullable=True, comment="本节课主题")
    summary = db.Column(db.Text, nullable=True, comment="课程总结")
    
    # 老师变更策略：优先使用课次老师，为空则回退到班级默认老师
    teacher = db.Column(db.String(64), nullable=True, comment="实际上课老师（可覆盖班级默认）")
    
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # 关联
    class_ref = db.relationship('Class', backref=db.backref('sessions', cascade='all, delete-orphan'))
    schedule_pattern = db.relationship('ClassSchedulePattern', backref='sessions')
    reschedule_from = db.relationship('ClassSession', remote_side=[id], backref='rescheduled_to')
    
    __table_args__ = (
        db.CheckConstraint("status IN ('scheduled', 'held', 'canceled', 'rescheduled')", 'check_session_status'),
    )


class SessionScore(db.Model):
    """打分明细表：记录老师对某节课中某位学生的一次打分动作"""
    __tablename__ = 'session_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    
    # 打分内容
    score_type = db.Column(db.String(8), nullable=False, comment="打分类别：Q/T/C/M1/M2/N")
    score = db.Column(db.Float, nullable=True, comment="分数 (0~5, 0 表示缺勤)")
    comment = db.Column(db.Text, nullable=True, comment="补充说明")
    
    # 记录人
    recorded_by = db.Column(db.String(32), nullable=False, comment="记录人")
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # 关联
    session = db.relationship('ClassSession', backref=db.backref('scores', cascade='all, delete-orphan'))
    student = db.relationship('Student', backref=db.backref('session_scores', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.CheckConstraint("score_type IN ('Q', 'T', 'C', 'M1', 'M2', 'N')", 'check_score_type'),
        db.CheckConstraint('score >= 0 AND score <= 5', 'check_score_range'),
    )
