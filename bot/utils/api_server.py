from flask import Flask, request, jsonify


def run_api(state, activity, host, port, auth_token, use_member_count=False):
    app = Flask(__name__)

    @app.route("/updateUsers", methods=["POST"])
    def update_users():
        if use_member_count:
            return jsonify({"error": "status locked to member count"}), 409
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {auth_token}":
            return jsonify({"error": "unauthorized"}), 401

        data = request.get_json(silent=True) or {}
        if "users" not in data or not isinstance(data["users"], int):
            return jsonify({"error": "invalid payload"}), 400

        state.users = data["users"]

        loop = activity.bot.loop
        if loop.is_running():
            loop.call_soon_threadsafe(lambda: activity.bot.create_task(activity.update_status()))

        return jsonify({"ok": True, "users": state.users})

    app.run(host=host, port=port)
