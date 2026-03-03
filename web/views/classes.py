from flask import Blueprint, render_template

from db import get_db

classes_bp = Blueprint('classes',__name__,url_prefix='/classes')

@classes_bp.route('/')
def list_classes():
    with get_db() as conn:
        classes = conn.execute(
            "SELECT * FROM classes WHERE status = 'active' ORDER BY id"
        ).fetchall()
    return render_template('classes/list.html',classes=classes)

# @bp.route('/',methods = ['POST'])
