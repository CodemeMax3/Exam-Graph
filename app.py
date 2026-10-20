from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from io import StringIO
import csv, json, time
from graph_engine import build_graph, dsatur, validate_coloring
from scheduler import make_sessions, build_timetable, validate_timetable

app = Flask(__name__)
CORS(app)

DATA = {
    "courses": [],
    "registrations": [],
    "settings": {
        "start_date": "2026-11-02",
        "dates": ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"],
        "sessions": [{"start": "09:00", "end": "11:00"}, {"start": "13:00", "end": "15:00"}]
    },
    "timetable": [],
    "last_algorithm": "DSatur"
}

def response_data():
    graph = build_graph(DATA["courses"], DATA["registrations"])
    return {
        "courses": DATA["courses"],
        "registrations": DATA["registrations"],
        "students": len({r["student_id"] for r in DATA["registrations"]}),
        "settings": DATA["settings"],
        "timetable": DATA["timetable"],
        "graph": {
            "nodes": [{"id": c["code"], "label": c["code"], "name": c["name"], "degree": len(graph.get(c["code"], set()))}
                      for c in DATA["courses"]],
            "edges": [{"source": a, "target": b} for a in graph for b in graph[a] if a < b]
        },
        "validation": validate_timetable(DATA["timetable"], graph) if DATA["timetable"] else {"valid": False, "message": "No timetable generated yet.", "conflicts": []}
    }

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": "ExamGraph API"})

@app.get("/api/state")
def state():
    return jsonify(response_data())

@app.post("/api/courses")
def add_course():
    body = request.get_json(force=True)
    code = str(body.get("code", "")).strip().upper()
    name = str(body.get("name", "")).strip()
    if not code or not name:
        return jsonify({"error": "Course code and course name are required."}), 400
    if any(c["code"] == code for c in DATA["courses"]):
        return jsonify({"error": f"Course code {code} already exists."}), 400
    try:
        duration = float(body.get("duration", 2))
        if duration <= 0: raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Duration must be a positive number of hours."}), 400
    DATA["courses"].append({"code": code, "name": name, "program": str(body.get("program", "General")), "duration": duration})
    DATA["timetable"] = []
    return jsonify(response_data()), 201

@app.delete("/api/courses/<code>")
def delete_course(code):
    DATA["courses"] = [c for c in DATA["courses"] if c["code"] != code.upper()]
    DATA["registrations"] = [r for r in DATA["registrations"] if r["course_code"] != code.upper()]
    DATA["timetable"] = []
    return jsonify(response_data())

@app.post("/api/registrations")
def add_registration():
    body = request.get_json(force=True)
    sid = str(body.get("student_id", "")).strip()
    name = str(body.get("student_name", "")).strip() or sid
    codes = body.get("courses", [])
    if not sid or not codes:
        return jsonify({"error": "Student ID and at least one course are required."}), 400
    known = {c["code"] for c in DATA["courses"]}
    unknown = [str(c).upper() for c in codes if str(c).upper() not in known]
    if unknown:
        return jsonify({"error": "Unknown course code(s): " + ", ".join(unknown)}), 400
    for code in codes:
        code = str(code).upper()
        existing = next((r for r in DATA["registrations"] if r["student_id"] == sid and r["course_code"] == code), None)
        if not existing:
            DATA["registrations"].append({"id": f"{sid}-{code}", "student_id": sid, "student_name": name, "course_code": code})
    DATA["timetable"] = []
    return jsonify(response_data()), 201

@app.delete("/api/registrations/<path:reg_id>")
def delete_registration(reg_id):
    DATA["registrations"] = [r for r in DATA["registrations"] if r["id"] != reg_id]
    DATA["timetable"] = []
    return jsonify(response_data())

@app.post("/api/import/courses")
def import_courses():
    if "file" not in request.files:
        return jsonify({"error": "Choose a CSV file."}), 400
    try:
        rows = csv.DictReader(StringIO(request.files["file"].read().decode("utf-8-sig")))
        added = 0
        existing = {c["code"] for c in DATA["courses"]}
        for row in rows:
            code = (row.get("course_code") or row.get("code") or "").strip().upper()
            name = (row.get("course_name") or row.get("name") or "").strip()
            if not code or not name: continue
            if code in existing: continue
            duration = float(row.get("duration_hours") or row.get("duration") or 2)
            if duration <= 0: continue
            DATA["courses"].append({"code": code, "name": name, "program": (row.get("program") or "General").strip(), "duration": duration})
            existing.add(code); added += 1
        DATA["timetable"] = []
        return jsonify({"message": f"Imported {added} course(s).", **response_data()})
    except Exception as exc:
        return jsonify({"error": f"Could not read courses CSV: {exc}"}), 400

@app.post("/api/import/registrations")
def import_registrations():
    if "file" not in request.files:
        return jsonify({"error": "Choose a CSV file."}), 400
    try:
        rows = list(csv.DictReader(StringIO(request.files["file"].read().decode("utf-8-sig"))))
        known = {c["code"] for c in DATA["courses"]}
        added = 0
        # Accept student_id/course_code rows OR student_id/student_name/courses rows.
        for row in rows:
            sid = (row.get("student_id") or "").strip()
            if not sid: continue
            student_name = (row.get("student_name") or sid).strip()
            if row.get("course_code"):
                codes = [row["course_code"].strip().upper()]
            else:
                raw = row.get("courses") or row.get("course_codes") or ""
                codes = [x.strip().upper() for x in raw.replace(";", ",").split(",") if x.strip()]
            unknown = [x for x in codes if x not in known]
            if unknown:
                return jsonify({"error": f"{sid} has unknown course code(s): {', '.join(unknown)}"}), 400
            for code in codes:
                if not any(r["student_id"] == sid and r["course_code"] == code for r in DATA["registrations"]):
                    DATA["registrations"].append({"id": f"{sid}-{code}", "student_id": sid, "student_name": student_name, "course_code": code})
                    added += 1
        DATA["timetable"] = []
        return jsonify({"message": f"Imported {added} registration(s).", **response_data()})
    except Exception as exc:
        return jsonify({"error": f"Could not read registrations CSV: {exc}"}), 400

@app.post("/api/generate")
def generate():
    if not DATA["courses"]:
        return jsonify({"error": "Add or import courses before generating a timetable."}), 400
    if not DATA["registrations"]:
        return jsonify({"error": "Add or import student registrations to detect course conflicts."}), 400
    graph = build_graph(DATA["courses"], DATA["registrations"])
    started = time.perf_counter()
    colors, trace = dsatur(graph)
    elapsed = (time.perf_counter() - started) * 1000
    coloring = validate_coloring(graph, colors)
    sessions = make_sessions(DATA["settings"])
    timetable, unplaced = build_timetable(DATA["courses"], colors, sessions)
    DATA["timetable"] = timetable
    DATA["last_algorithm"] = "DSatur"
    result = response_data()
    result["algorithm"] = {"name": "DSatur", "trace": trace, "colors_used": len(set(colors.values())), "execution_ms": round(elapsed, 3)}
    result["coloring_validation"] = coloring
    result["unplaced"] = unplaced
    result["message"] = "Timetable generated with DSatur." if not unplaced else "Some courses could not be placed because more sessions are needed."
    return jsonify(result)

@app.put("/api/settings")
def settings():
    body = request.get_json(force=True)
    dates = body.get("dates", DATA["settings"]["dates"])
    sessions = body.get("sessions", DATA["settings"]["sessions"])
    if not dates or not sessions:
        return jsonify({"error": "Add at least one date and one session."}), 400
    DATA["settings"] = {"start_date": dates[0], "dates": dates, "sessions": sessions}
    DATA["timetable"] = []
    return jsonify(response_data())


@app.post("/api/reset")
def reset():
    DATA["courses"], DATA["registrations"], DATA["timetable"] = [], [], []
    return jsonify(response_data())

@app.get("/api/export/csv")
def export_csv():
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["date","start","end","course_code","course_name","color"])
    writer.writeheader()
    for row in DATA["timetable"]: writer.writerow(row)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=examgraph_timetable.csv"})

@app.get("/api/export/json")
def export_json():
    return Response(json.dumps(response_data(), indent=2), mimetype="application/json", headers={"Content-Disposition":"attachment; filename=examgraph_project.json"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
