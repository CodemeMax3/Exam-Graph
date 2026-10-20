from datetime import datetime, timedelta

def make_sessions(settings):
    sessions = []
    for date in settings.get("dates", []):
        for index, item in enumerate(settings.get("sessions", []), start=1):
            sessions.append({"date": date, "start": item["start"], "end": item["end"], "session_number": index})
    return sessions

def build_timetable(courses, colors, sessions):
    course_by_code = {c["code"]: c for c in courses}
    color_order = sorted(set(colors.values()))
    timetable, unplaced = [], []
    for color in color_order:
        course_codes = sorted([code for code, assigned in colors.items() if assigned == color])
        session = next((s for s in sessions if _session_fits(s, [course_by_code[c] for c in course_codes])), None)
        if not session:
            unplaced.extend(course_codes)
            continue
        for code in course_codes:
            course = course_by_code[code]
            timetable.append({
                "date": session["date"], "start": session["start"], "end": session["end"],
                "course_code": code, "course_name": course["name"], "color": color,
                "duration": course.get("duration", 2), "session_number": session["session_number"]
            })
    return timetable, unplaced

def _session_fits(session, courses):
    try:
        start = datetime.strptime(session["start"], "%H:%M")
        end = datetime.strptime(session["end"], "%H:%M")
        hours = (end-start).total_seconds()/3600
        return all(float(c.get("duration", 2)) <= hours for c in courses)
    except Exception:
        return False

def validate_timetable(timetable, graph):
    conflicts = []
    assigned = {}
    for row in timetable:
        key = (row["date"], row["start"], row["end"])
        code = row["course_code"]
        assigned[code] = key
    for a, neighbors in graph.items():
        for b in neighbors:
            if a < b and a in assigned and assigned.get(a) == assigned.get(b):
                conflicts.append({"course_a": a, "course_b": b, "message": f"{a} and {b} share the same session."})
    return {"valid": not conflicts, "conflicts": conflicts, "message": "Timetable has no same-session conflicts." if not conflicts else "Timetable contains conflicts."}
