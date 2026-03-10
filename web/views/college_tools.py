from flask import Blueprint, render_template

college_tools_bp = Blueprint('college_tools', __name__)

@college_tools_bp.route('/college-tools')
def college_tools():
    return render_template('college_tools.html')
