from flask import Flask, session, redirect
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

from routes import auth
from routes import admin
from routes import dashboard
from routes import test

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "fallback-change-me")
app.permanent_session_lifetime = timedelta(hours=5)

app.register_blueprint(auth.bp, url_prefix="/auth")
app.register_blueprint(admin.bp, url_prefix="/admin")
app.register_blueprint(dashboard.bp, url_prefix="/dashboard")
app.register_blueprint(test.bp, url_prefix="/test")

@app.route("/")
def index():
    return redirect("/auth/login")

@app.errorhandler(404)
def not_found(error):
    return "404 Page Not Found", 404

@app.errorhandler(500)
def server_error(error):
    return "500 Internal Server Error", 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=6001, threaded=True)
