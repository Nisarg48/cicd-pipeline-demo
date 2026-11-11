import os

import bcrypt
import pymysql
from flask import Flask, jsonify, request, session
from pymysql.cursors import DictCursor

app = Flask(__name__)

secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required")
app.secret_key = secret_key


def get_db_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        connect_timeout=5,
        cursorclass=DictCursor,
    )


def public_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok"), 200


@app.route("/health/db", methods=["GET"])
def health_db():
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        finally:
            connection.close()
    except Exception:
        app.logger.exception("Database health check failed")
        return jsonify(status="error", error="database unavailable"), 500

    return jsonify(status="ok"), 200


@app.route("/version", methods=["GET"])
def version():
    return jsonify(
        sha=os.environ.get("BUILD_SHA", "unknown"),
        build_time=os.environ.get("BUILD_TIME", "unknown"),
    )


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify(error="username, email and password are required"), 400

    if len(password.encode("utf-8")) > 72:
        return jsonify(error="password must be 72 bytes or fewer"), 400

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) "
                "VALUES (%s, %s, %s)",
                (username, email, password_hash),
            )
            user_id = cursor.lastrowid
        connection.commit()
    except pymysql.err.IntegrityError:
        connection.rollback()
        return jsonify(error="username or email already exists"), 409
    except pymysql.MySQLError:
        connection.rollback()
        app.logger.exception("Failed to register user")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    return jsonify(id=user_id, username=username, email=email), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify(error="username/email and password are required"), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email, password_hash FROM users "
                "WHERE username = %s OR email = %s LIMIT 1",
                (identifier, identifier),
            )
            user = cursor.fetchone()
    except pymysql.MySQLError:
        app.logger.exception("Failed to log in user")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    if not user or not bcrypt.checkpw(
        password.encode("utf-8"), user["password_hash"].encode("utf-8")
    ):
        return jsonify(error="invalid credentials"), 401

    session.clear()
    session["user_id"] = user["id"]

    return jsonify(public_user(user)), 200


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(status="ok"), 200


@app.route("/api/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify(error="not logged in"), 401

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email FROM users WHERE id = %s",
                (user_id,),
            )
            user = cursor.fetchone()
    except pymysql.MySQLError:
        app.logger.exception("Failed to load current user")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    if not user:
        session.clear()
        return jsonify(error="not logged in"), 401

    return jsonify(public_user(user)), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
