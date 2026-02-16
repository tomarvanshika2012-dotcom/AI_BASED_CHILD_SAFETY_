from flask import Flask, request, jsonify

app = Flask(__name__)

children = []

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    children.append(data)
    return jsonify({"message": "Registered successfully"}), 200

@app.route("/children", methods=["GET"])
def get_children():
    return jsonify(children), 200


if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(debug=True, port=5000)
