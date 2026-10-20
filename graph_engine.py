from collections import defaultdict

def build_graph(courses, registrations):
    graph = {c["code"]: set() for c in courses}
    by_student = defaultdict(set)
    for row in registrations:
        code = row.get("course_code")
        sid = row.get("student_id")
        if code in graph and sid:
            by_student[sid].add(code)
    for codes in by_student.values():
        for a in codes:
            for b in codes:
                if a != b:
                    graph[a].add(b)
    return graph

def dsatur(graph):
    colors = {}
    trace = []
    degree = {v: len(neighbors) for v, neighbors in graph.items()}
    while len(colors) < len(graph):
        uncolored = [v for v in graph if v not in colors]
        def priority(v):
            saturation = len({colors[n] for n in graph[v] if n in colors})
            return (-saturation, -degree[v], v)
        vertex = sorted(uncolored, key=priority)[0]
        used = {colors[n] for n in graph[vertex] if n in colors}
        color = 1
        while color in used:
            color += 1
        saturation_before = len(used)
        colors[vertex] = color
        trace.append({
            "step": len(trace) + 1, "course_code": vertex,
            "saturation_degree": saturation_before, "vertex_degree": degree[vertex],
            "color": color
        })
    return colors, trace

def validate_coloring(graph, colors):
    conflicts = []
    for a, neighbors in graph.items():
        for b in neighbors:
            if a < b and colors.get(a) == colors.get(b):
                conflicts.append({"course_a": a, "course_b": b, "message": f"{a} and {b} share a color."})
    return {"valid": not conflicts, "conflicts": conflicts, "message": "All graph conflicts are separated." if not conflicts else "Color conflicts found."}
