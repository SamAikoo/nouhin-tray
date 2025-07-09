from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # セッション管理に必要
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # 未ログイン時のリダイレクト先

# --------------------
# Userモデル
# --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    deadline = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="進行中")
    memo = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 紐づくユーザー
    files = db.relationship("ProjectFile", backref="project", lazy=True)

class ProjectFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now())


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'zip', 'png', 'jpg', 'jpeg', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload/<int:project_id>", methods=["POST"])
@login_required
def upload_file(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)

    file = request.files["file"]
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        new_file = ProjectFile(filename=filename, project_id=project.id)
        db.session.add(new_file)
        db.session.commit()

    return redirect(url_for("dashboard"))


# --------------------
# ログイン関連のコールバック
# --------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------
# ルーティング
# --------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("ログイン失敗。ユーザー名またはパスワードが違います。")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        title = request.form["title"]
        deadline = request.form["deadline"]
        status = request.form["status"]
        memo = request.form["memo"]
        project = Project(
            title=title,
            deadline=deadline,
            status=status,
            memo=memo,
            user_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        return redirect(url_for("dashboard"))

    # このユーザーの案件だけ表示
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", projects=projects)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))



from flask import abort

@app.route("/edit_project/<int:project_id>", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)  # 他のユーザーの編集は禁止

    if request.method == "POST":
        project.title = request.form["title"]
        project.deadline = request.form["deadline"]
        project.status = request.form["status"]
        project.memo = request.form["memo"]
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("edit_project.html", project=project)

@app.route("/delete_project/<int:project_id>", methods=["POST"])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)  # 他のユーザーの削除は禁止

    db.session.delete(project)
    db.session.commit()
    return redirect(url_for("dashboard"))



# --------------------
# 初回DB作成
# --------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)


