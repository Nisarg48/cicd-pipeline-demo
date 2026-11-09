import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok"), 200


@app.route("/version", methods=["GET"])
def version():
    return jsonify(
        sha=os.environ.get("BUILD_SHA", "unknown"),
        build_time=os.environ.get("BUILD_TIME", "unknown"),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
