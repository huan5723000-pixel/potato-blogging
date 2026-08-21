from datetime import date
from typing import List

from flask import Flask, abort, render_template, redirect, url_for, flash,request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_migrate import Migrate

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

#ADMIN DECORATOR
def user_admin(f):
    @wraps(f)
    def check_admin(*args, **kwargs):
        if not current_user.id == 1:
            abort(403) #stops flask immediately
        return f(*args, **kwargs)
    return check_admin 

    # CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# TODO: Create a User table for all your registered users.
#This would be the parent
migrate = Migrate(app, db)
class User(UserMixin, db.Model):
    __tablename__ = "users_table"
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(1000))
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    #statement to state 1 user have Many posts: function:"Give all post by this user"
    posts: Mapped[List["BlogPost"]] = relationship(back_populates="user")
    #LINKING COMMENT
    comments: Mapped[List["Comment"]] = relationship(back_populates="user")

#This would be the child
# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # author: Mapped[str] = mapped_column(String(250), nullable=False) #___Deleted because you can call it using the link between the post and user
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    #link post to user
    #the user_id: the actual column stored int he database
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey("users_table.id"))
    #function: "give me user who wrote this"
    user: Mapped["User"] = relationship(back_populates="posts")
    #Foreignkey is like a "pointer" basicly use user_table.id to point to user.
    #LINKING COMMENT:
    comments: Mapped[List["Comment"]] = relationship(back_populates="post")


class Comment(db.Model):
    __tablename__ = "comments_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)

    #link Comment to User
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey("users_table.id"))
    user: Mapped["User"] = relationship(back_populates="comments")

    #link Comment to Post
    post_id: Mapped[int] = mapped_column(Integer,ForeignKey("blog_posts_table.id"))
    post: Mapped["BlogPost"] = relationship(back_populates="comments")



with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET', 'POST'])
def register():
    reg_form = RegisterForm()
    if reg_form.validate_on_submit():
        #check first
        existing_user = User.query.filter_by(email=request.form.get("email").lower()).first()
        if existing_user:
            #flash messages are on the html which it's going to be displayed
            flash("Email already registered, please log in", "danger")
            return redirect(url_for("login"))

        try:
            hashed_password = generate_password_hash(
                password=request.form.get('password'),
                method='pbkdf2:sha256',
                salt_length=8)

            user_profile = User(
                email=request.form.get("email").lower(),
                password=hashed_password,
                name = request.form.get("name")
            )
            db.session.add(user_profile)
            db.session.commit()
            print("success registration")
            return redirect(url_for("login"))

        except Exception as error:
            print(error)
            db.session.rollback()

    return render_template("register.html",form = reg_form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        form_email = request.form.get("email")
        user = db.session.execute(db.select(User).where(User.email == form_email.lower())).scalar()

        if user and check_password_hash(user.password, login_form.password.data):
            login_user(user)
            print("login success")
            return redirect(url_for("get_all_posts"))

        else :
            flash("Invalid username or password", "danger")


    return render_template("login.html",form = login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>",methods= ["GET","POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash ("Please log in to comment")
            return redirect(url_for("login"))

        new_comment = Comment(
            comment=form.comment.data,
            date=date.today().strftime("%B %d, %Y"),
            user=current_user,
            post=requested_post,
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post",post_id=post_id))

    return render_template("post.html", post=requested_post,comment_form=form,comments = requested_post.comments) #to show ALL comments not just the new one


# TODO: Use a decorator so only an admin user can create a new post
#always log in before checking if its admin
@app.route("/new-post", methods=["GET", "POST"])
@login_required
@user_admin
def add_new_post():
    form = CreatePostForm()
    print(current_user)
    print(current_user.id)
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y"),
            user = current_user,
        )
        db.session.add(new_post)
        db.session.commit()
        print(current_user)
        print(current_user.id)
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
@user_admin
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        user =current_user,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@login_required
@user_admin
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True, port=5002)
