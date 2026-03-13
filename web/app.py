# app.py
from flask import Flask
from .views.students import students_bp
from .views.classes import classes_bp
from .views.index import index_bp
from .views.college_tools import college_tools_bp

# optional: load environment variables from a .env file if present. this
# keeps deployment flexible but doesn't make python-dotenv a hard requirement.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import get_config

# SQLAlchemy & Migrate
from db.sa_db import db
from flask_migrate import Migrate



# create application and load configuration
app = Flask(__name__)
app.config.from_object(get_config())

# 初始化 SQLAlchemy

# 导入所有模型，确保 Flask-Migrate 能识别
from db import models
db.init_app(app)
migrate = Migrate(app, db)

# filter to render document type in human-friendly Chinese
@app.template_filter('format_doc_type')
def format_doc_type(code: str) -> str:
    if not code:
        return ''
    # passports (including country suffix) should show 护照 or 护照-国家
    if code.startswith('PASSPORT'):
        parts = code.split('-', 1)
        if len(parts) == 2 and parts[1]:
            return '护照-' + parts[1]
        return '护照'
    mapping = {
        'ID_CARD': '身份证',
        'HMT_PASS': '港澳台通行证',
        'OTHER': '其他',
    }
    return mapping.get(code, code)


# filter to choose a display name for a student
@app.template_filter('format_student_name')
def format_student_name(student) -> str:
    """Return the preferred name for a student.

    * if the ``display_name`` field is present, use it (常用称呼)
    * otherwise inspect ``student.documents`` for the first non-empty
      ``doc_name`` and use that (证件名称)
    * fall back to ``student.student_number`` or an empty string.
    """
    if not student:
        return ''
    if getattr(student, 'display_name', None):
        return student.display_name
    # look for document name
    for doc in getattr(student, 'documents', []) or []:
        if getattr(doc, 'doc_name', None):
            return doc.doc_name
    return getattr(student, 'student_number', '') or ''


# filter to format class number as level-paddedGroup
@app.template_filter('format_class_number')
def format_class_number(cls) -> str:
    """Format a class number for display.

    Primary form is ``level-期数`` where 期数 is two digits.  Accepts either an
    ORM object or a mapping (dict) produced by views.  If one field is missing
    we fall back gracefully:

    * both present: ``U9B-01``
    * only level: ``U9B``
    * only group: ``01`` (still padded)
    * neither: ``''``
    """
    if not cls:
        return ''
    # extract fields from object or dict
    if hasattr(cls, 'get') and not hasattr(cls, '__table__'):
        level = cls.get('level') or ''
        grp = cls.get('group_number')
    else:
        level = getattr(cls, 'level', None) or ''
        grp = getattr(cls, 'group_number', None)
    num = ''
    if grp is not None:
        try:
            num = f"{int(grp):02d}"
        except Exception:
            num = str(grp)
    if level and num:
        return f"{level}-{num}"
    if level:
        return level
    if num:
        return num
    return ''
# during development we can auto-create missing tables
with app.app_context():
    try:
        from db.schema import init_db
        init_db()
    except Exception:
        pass

app.register_blueprint(students_bp)
app.register_blueprint(classes_bp)
app.register_blueprint(index_bp)
app.register_blueprint(college_tools_bp)

if __name__ == '__main__':
    app.run(debug=True)
