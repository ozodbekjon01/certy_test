from flask import Flask, session, redirect
from datetime import timedelta

from routes import auth
from routes import admin
from routes import dashboard
from routes import test


# =========================================
# APP
# =========================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "super-secret-key"

# session vaqti
app.permanent_session_lifetime = timedelta(hours=5)


# =========================================
# REGISTER BLUEPRINTS
# =========================================

app.register_blueprint(auth.bp, url_prefix="/auth")
app.register_blueprint(admin.bp, url_prefix="/admin")
app.register_blueprint(dashboard.bp, url_prefix="/dashboard")
app.register_blueprint(test.bp, url_prefix="/test")


# =========================================
# HOME
# =========================================

@app.route("/")
def index():
    return redirect("/auth/login")



# =========================================
# ERROR HANDLERS
# =========================================

@app.errorhandler(404)
def not_found(error):
    return "404 Page Not Found", 404


@app.errorhandler(500)
def server_error(error):
    return "500 Internal Server Error", 500


# =========================================
# RUN
# =========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=6000
    )