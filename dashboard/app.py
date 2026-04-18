"""Flask dashboard for the OTA and charger security demo."""

from __future__ import annotations

from flask import Flask, jsonify, render_template

from core.demo_runner import build_demo_report


def create_app() -> Flask:
	app = Flask(__name__, template_folder="templates", static_folder="static")

	@app.get("/")
	def index() -> str:
		return render_template("index.html")

	@app.get("/api/report")
	def report() -> tuple[dict, int]:
		return jsonify(build_demo_report()), 200

	@app.get("/api/scenarios")
	def scenarios() -> tuple[dict, int]:
		report = build_demo_report()
		return jsonify({"scenarios": report["scenarios"], "metrics": report["metrics"]}), 200

	return app


app = create_app()


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)