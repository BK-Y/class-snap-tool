from flask_sqlalchemy import SQLAlchemy

# 全局 SQLAlchemy 实例
# 在 app.py 里 db.init_app(app)
db = SQLAlchemy()
