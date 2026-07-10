from flask import render_template, request, session, url_for, redirect
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User

def register_auth_routes(app):
    @app.route("/auth", methods=["GET", "POST"])
    def auth():
        if request.method == "POST":
            auth_mode = request.form.get("auth_mode", "login")
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not email or not password:
                return render_template("auth.html", error="Email and password are required.")

            if auth_mode == "signup":
                username = request.form.get("username", "").strip()
                if not username:
                    username = email.split("@")[0]

                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    return render_template("auth.html", error="An account with this email already exists.")

                # SECURITY: Always register as regular user, never admin
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    is_admin=False
                )
                db.session.add(user)
                db.session.commit()
                session["user_id"] = user.id
                session["is_admin"] = False
                
                next_url = session.pop("next_url", None)
                return redirect(next_url or url_for("index"))

            # LOGIN mode
            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                return render_template("auth.html", error="Invalid email or password.")

            session["user_id"] = user.id
            session["is_admin"] = user.is_admin
            
            next_url = session.pop("next_url", None)
            return redirect(next_url or url_for("index"))

        if session.get("user_id"):
            return redirect(url_for("index"))

        return render_template("auth.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))
