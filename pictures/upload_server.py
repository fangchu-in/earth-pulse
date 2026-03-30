from flask import Flask, request
import os

app = Flask(__name__)

UPLOAD_FOLDER = "/home/fangchu/earth_pulse/pictures/raw"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files['file']
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    return "OK"

app.run(host="0.0.0.0", port=5000)