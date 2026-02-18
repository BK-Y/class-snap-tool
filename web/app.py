# app.py
from flask import Flask
from .views.students import students_bp
from .views.classes import classes_bp
from .views.index import index_bp 
from db import init_db  # 导入你写的数据库模块

app = Flask(__name__)
app.secret_key = "test"
init_db()
'''
with app.app_context():
    db.init_db()  # 自动初始化数据库
'''
app.register_blueprint(students_bp)
app.register_blueprint(classes_bp)
app.register_blueprint(index_bp)

if __name__ == '__main__':
    app.run(debug=True)
