"""Flask API for the AI Project Intelligence & Risk Advisor."""
from pathlib import Path
from threading import RLock

from flask import Flask, jsonify, render_template, request, Response
from werkzeug.utils import secure_filename

from engine import KB, analyze, answer, build_markdown, build_docx

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {"pdf", "docx", "csv", "txt", "md"}
MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_TOTAL_SIZE = 100 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_TOTAL_SIZE
LOCK = RLock()
STATE = {"kb": KB(), "analysis": None, "files": []}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def rebuild():
    kb = KB()
    for filename, data in STATE["files"]:
        kb.add(filename, data)
    kb.build()
    STATE["kb"] = kb
    STATE["analysis"] = analyze(kb) if kb.docs else None

def current_state():
    kb = STATE["kb"]
    return {
        "docs": kb.docs,
        "lines": len(kb.lines),
        "chunks": len(kb.chunks),
        "tasks": len(kb.tasks),
        "analysis": STATE["analysis"],
        "retrieval_mode": kb.retrieval_mode,
    }

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/state")
def get_state():
    with LOCK:
        return jsonify(current_state())

@app.post("/api/upload")
def upload():
    incoming = request.files.getlist("files")
    if not incoming or all(not f.filename for f in incoming):
        return jsonify({"error": "Choose at least one file to upload."}), 400
    accepted, skipped = [], []
    with LOCK:
        for file in incoming:
            if not file.filename:
                continue
            filename = secure_filename(file.filename)
            if not allowed_file(filename):
                skipped.append(f"{filename}: unsupported type")
                continue
            data = file.read()
            if len(data) > MAX_FILE_SIZE:
                skipped.append(f"{filename}: exceeds 20 MB")
                continue
            try:
                probe = KB()
                probe.add(filename, data)
                if not probe.docs:
                    raise ValueError("No readable content")
                accepted.append((filename, data))
            except Exception as exc:
                skipped.append(f"{filename}: {exc}")
        if accepted:
            files_by_name = {name: data for name, data in STATE["files"]}
            files_by_name.update(accepted)
            STATE["files"] = list(files_by_name.items())
            rebuild()
        result = current_state()
    result["uploaded"] = [name for name, _ in accepted]
    result["skipped"] = skipped
    return jsonify(result)

@app.post("/api/sample")
def sample():
    folder = BASE_DIR / "sample_docs"
    files = [(p.name, p.read_bytes()) for p in sorted(folder.iterdir())
             if p.is_file() and allowed_file(p.name)]
    if not files:
        return jsonify({"error": "Sample documents are missing."}), 500
    with LOCK:
        STATE["files"] = files
        rebuild()
        return jsonify(current_state())

@app.post("/api/reset")
def reset():
    with LOCK:
        STATE["files"] = []
        rebuild()
        return jsonify(current_state())

@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("q", "")).strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    with LOCK:
        if STATE["analysis"] is None:
            return jsonify({"error": "Upload project documents first."}), 400
        result = answer(STATE["kb"], STATE["analysis"], question)
    return jsonify({"answer": result})

@app.get("/api/download")
def download():
    with LOCK:
        if STATE["analysis"] is None:
            return "Upload project documents first.", 400
        report = build_markdown(STATE["analysis"])
    return Response(report, mimetype="text/markdown",
                    headers={"Content-Disposition": "attachment; filename=project-documentation.md"})

@app.get("/api/download.docx")
def download_docx():
    with LOCK:
        if STATE["analysis"] is None:
            return "Upload project documents first.", 400
        data = build_docx(STATE["analysis"])
    return Response(data, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": "attachment; filename=project-report.docx"})

@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify({"error": "Total upload size exceeds 100 MB."}), 413

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
