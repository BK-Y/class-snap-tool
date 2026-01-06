# app.py
from flask import Flask
from routes.students import students_bp
from routes.classes import classes_bp
import db  # 导入你写的数据库模块

app = Flask(__name__)
app.register_blueprint(students_bp)
app.register_blueprint(classes_bp)

if __name__ == '__main__':
    db.init_db()  # 自动初始化数据库
    app.run(debug=True)
