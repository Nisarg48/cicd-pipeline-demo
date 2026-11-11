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

POST_SELECT = (
    "SELECT p.id, p.title, p.body, p.created_at, p.updated_at, "
    "u.id AS author_id, u.username AS author_username, u.email AS author_email "
    "FROM posts p JOIN users u ON u.id = p.user_id"
)

COMMENT_SELECT = (
    "SELECT c.id, c.body, c.created_at, "
    "u.id AS author_id, u.username AS author_username, u.email AS author_email "
    "FROM comments c JOIN users u ON u.id = c.user_id"
)


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


def mask_email(email):
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{local[:2]}***@{domain}"


def public_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
    }


def public_author(row):
    return {
        "id": row["author_id"],
        "username": row["author_username"],
        "email": mask_email(row["author_email"]),
    }


def serialize_post(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "body": row["body"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "author": public_author(row),
    }


def serialize_comment(row):
    return {
        "id": row["id"],
        "body": row["body"],
        "created_at": row["created_at"].isoformat(),
        "author": public_author(row),
    }


def require_login():
    user_id = session.get("user_id")
    if user_id is None:
        return None, (jsonify(error="not logged in"), 401)
    return user_id, None


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


@app.route("/api/posts", methods=["GET"])
def list_posts():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                POST_SELECT + " ORDER BY p.created_at DESC, p.id DESC"
            )
            posts = cursor.fetchall()
    except pymysql.MySQLError:
        app.logger.exception("Failed to list posts")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    return jsonify([serialize_post(post) for post in posts]), 200


@app.route("/api/posts/<int:post_id>", methods=["GET"])
def get_post(post_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(POST_SELECT + " WHERE p.id = %s", (post_id,))
            post = cursor.fetchone()

            if not post:
                return jsonify(error="post not found"), 404

            cursor.execute(
                COMMENT_SELECT
                + " WHERE c.post_id = %s ORDER BY c.created_at ASC, c.id ASC",
                (post_id,),
            )
            comments = cursor.fetchall()
    except pymysql.MySQLError:
        app.logger.exception("Failed to load post")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    result = serialize_post(post)
    result["comments"] = [serialize_comment(comment) for comment in comments]
    return jsonify(result), 200


@app.route("/api/posts", methods=["POST"])
def create_post():
    user_id, error = require_login()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()

    if not title or not body:
        return jsonify(error="title and body are required"), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO posts (user_id, title, body) VALUES (%s, %s, %s)",
                (user_id, title, body),
            )
            post_id = cursor.lastrowid
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute(POST_SELECT + " WHERE p.id = %s", (post_id,))
            post = cursor.fetchone()
    except pymysql.MySQLError:
        connection.rollback()
        app.logger.exception("Failed to create post")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    return jsonify(serialize_post(post)), 201


@app.route("/api/posts/<int:post_id>", methods=["PUT"])
def update_post(post_id):
    user_id, error = require_login()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()

    if not title or not body:
        return jsonify(error="title and body are required"), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
            post = cursor.fetchone()

            if not post:
                return jsonify(error="post not found"), 404

            if post["user_id"] != user_id:
                return jsonify(error="forbidden"), 403

            cursor.execute(
                "UPDATE posts SET title = %s, body = %s, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (title, body, post_id),
            )
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute(POST_SELECT + " WHERE p.id = %s", (post_id,))
            post = cursor.fetchone()
    except pymysql.MySQLError:
        connection.rollback()
        app.logger.exception("Failed to update post")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    return jsonify(serialize_post(post)), 200


@app.route("/api/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    user_id, error = require_login()
    if error:
        return error

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
            post = cursor.fetchone()

            if not post:
                return jsonify(error="post not found"), 404

            if post["user_id"] != user_id:
                return jsonify(error="forbidden"), 403

            cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        connection.commit()
    except pymysql.MySQLError:
        connection.rollback()
        app.logger.exception("Failed to delete post")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    return jsonify(status="deleted"), 200


@app.route("/api/posts/<int:post_id>/comments", methods=["POST"])
def create_comment(post_id):
    user_id, error = require_login()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()

    if not body:
        return jsonify(error="body is required"), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
            if not cursor.fetchone():
                return jsonify(error="post not found"), 404

            cursor.execute(
                "INSERT INTO comments (post_id, user_id, body) "
                "VALUES (%s, %s, %s)",
                (post_id, user_id, body),
            )
            comment_id = cursor.lastrowid
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute(COMMENT_SELECT + " WHERE c.id = %s", (comment_id,))
            comment = cursor.fetchone()
    except pymysql.MySQLError:
        connection.rollback()
        app.logger.exception("Failed to create comment")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    return jsonify(serialize_comment(comment)), 201


@app.route("/api/comments/<int:comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    user_id, error = require_login()
    if error:
        return error

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM comments WHERE id = %s", (comment_id,)
            )
            comment = cursor.fetchone()

            if not comment:
                return jsonify(error="comment not found"), 404

            if comment["user_id"] != user_id:
                return jsonify(error="forbidden"), 403

            cursor.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
        connection.commit()
    except pymysql.MySQLError:
        connection.rollback()
        app.logger.exception("Failed to delete comment")
        return jsonify(error="database error"), 500
    finally:
        connection.close()

    return jsonify(status="deleted"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
