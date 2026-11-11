import os

import pymysql
from flask import Flask, jsonify

app = Flask(__name__)


def get_db_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        connect_timeout=5,
    )


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
