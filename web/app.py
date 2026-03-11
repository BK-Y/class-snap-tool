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
