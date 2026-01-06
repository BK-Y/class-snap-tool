from flask import Blueprint, render_template,request,redirect

from db import get_db_connection

classes_bp = Blueprint('classes',__name__,url_prefix='/classes')

@classes_bp.route('/')
def list_classes():
    db = get_db_connection()
    classes = db.execute(
        "SELECT * FROM classes WHERE status = 'active' ORDER BY id"
    ).fetchall()
    return render_template('classes/list.html',classes=classes)

# @bp.route('/',methods = ['POST'])
