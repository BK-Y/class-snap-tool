from flask import Blueprint,redirect,url_for,request,render_template

import db
index_bp = Blueprint('index',__name__)

@index_bp.route('/')
def index():
    return render_template('index.html')
