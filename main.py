from dashboard.app import app, socketio

if __name__ == "__main__":
    print("PQ-AUTO dashboard -> http://127.0.0.1:5000")
    socketio.run(app, debug=False, host="127.0.0.1", port=5000, allow_unsafe_werkzeug=True)
