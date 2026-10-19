#!/usr/bin/env python3
"""Local answer validation. Uses only Python's standard library; not a server checker."""
import argparse
import json
import math
from pathlib import Path
import re
import sys


class InvalidAnswer(ValueError):
    pass


def integers(text):
    tokens = text.split()
    if any(re.fullmatch(r"[+-]?[0-9]+", token) is None for token in tokens):
        raise ValueError("Expected integer tokens only")
    return [int(token) for token in tokens]


def read_instance(task, text):
    a = integers(text)
    if not a:
        raise ValueError("Empty input")
    n = a[0]
    if task == "A":
        if len(a) != 2 + 2 * n or not 2 <= n <= 2000:
            raise ValueError("Invalid A input size")
        capacity = a[1]
        items = list(zip(a[2::2], a[3::2]))
        if not 1 <= capacity <= 10**12:
            raise ValueError("Invalid capacity")
        if any(not 1 <= w <= min(capacity, 10**9) or not 2 <= p <= 10**9 for w, p in items):
            raise ValueError("Invalid item")
        if sum(w for w, _ in items) <= capacity:
            raise ValueError("All items must not fit together")
        return {"n": n, "capacity": capacity, "items": items}
    if task == "B":
        if len(a) != 1 + 2 * n or not 3 <= n <= 5000:
            raise ValueError("Invalid B input size")
        points = list(zip(a[1::2], a[2::2]))
        if len(set(points)) != n or any(abs(v) > 10**6 for v in a[1:]):
            raise ValueError("Invalid coordinates")
        return {"n": n, "points": points}
    if task == "C":
        if len(a) < 2:
            raise ValueError("Missing worker count")
        k = a[1]
        if not 2 <= n <= 500 or not 1 <= k <= min(20, n) or len(a) != 2 + n + (n + 1)**2:
            raise ValueError("Invalid C input size")
        service = [0] + a[2:2+n]
        if any(not 1 <= s <= 3600 for s in service[1:]):
            raise ValueError("Invalid service time")
        flat = a[2+n:]
        d = [flat[i*(n+1):(i+1)*(n+1)] for i in range(n+1)]
        for i in range(n+1):
            for j in range(n+1):
                if (i == j and d[i][j] != 0) or (i != j and not 1 <= d[i][j] <= 10**6):
                    raise ValueError("Invalid travel time")
                if d[i][j] != d[j][i]:
                    raise ValueError("Asymmetric matrix")
        return {"n": n, "k": k, "service": service, "d": d}
    raise ValueError("Unknown task")


def route_time(data, route):
    if not route:
        return 0
    seq = [0] + list(route) + [0]
    return sum(data["d"][u][v] for u, v in zip(seq, seq[1:])) + sum(data["service"][v] for v in route)


def evaluate(task, data, answer):
    n = data["n"]
    try:
        a = integers(answer)
    except ValueError as exc:
        raise InvalidAnswer(str(exc)) from exc
    if task == "A":
        if not a or not 0 <= a[0] <= n or len(a) != a[0] + 1:
            raise InvalidAnswer("Expected m followed by exactly m item indices")
        selected = a[1:]
        if any(not 1 <= i <= n for i in selected) or len(set(selected)) != len(selected):
            raise InvalidAnswer("Invalid or duplicate item index")
        weight = sum(data["items"][i-1][0] for i in selected)
        if weight > data["capacity"]:
            raise InvalidAnswer("Budget exceeded")
        quality = math.fsum(math.log(data["items"][i-1][1]) for i in sorted(selected))
        return {"quality": quality, "weight": weight, "selected": len(selected)}
    if task == "B":
        if len(a) != n + 1 or a[0] != 1 or a[-1] != 1:
            raise InvalidAnswer("Expected n+1 indices starting and ending at 1")
        if sorted(a[:-1]) != list(range(1, n+1)):
            raise InvalidAnswer("Each vertex must appear once before the closing 1")
        edges = sorted((min(u, v), max(u, v)) for u, v in zip(a, a[1:]))
        points = data["points"]
        quality = math.fsum(math.hypot(points[u-1][0]-points[v-1][0], points[u-1][1]-points[v-1][1]) for u, v in edges)
        return {"quality": quality}
    lines = answer.strip().splitlines()
    if len(lines) != data["k"]:
        raise InvalidAnswer("Expected exactly k route lines")
    routes = []
    for line in lines:
        row = integers(line)
        if not row or not 0 <= row[0] <= n or len(row) != row[0] + 1:
            raise InvalidAnswer("Expected m followed by exactly m task indices on each line")
        routes.append(row[1:])
    selected = [v for route in routes for v in route]
    if sorted(selected) != list(range(1, n+1)):
        raise InvalidAnswer("Every task must be assigned exactly once")
    times = [route_time(data, route) for route in routes]
    return {"quality": max(times), "worker_times": times}


def score(task, quality, reference):
    if not math.isfinite(reference) or reference <= 0:
        raise ValueError("Reference must be finite and positive")
    rho = quality / reference if task == "A" else reference / quality
    if rho >= 1 - 1e-12:
        rho = 1.0
    return 10 * min(1.0, max(0.0, rho))**10


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["A", "B", "C"])
    parser.add_argument("input", type=Path)
    parser.add_argument("answer", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    try:
        data = read_instance(args.task, args.input.read_text(encoding="utf-8"))
        ref = float(args.reference.read_text().strip()) if args.reference else None
        if ref is not None and (not math.isfinite(ref) or ref <= 0):
            raise ValueError("Reference must be finite and positive")
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "INPUT_ERROR", "message": str(exc)}, ensure_ascii=False))
        return 2
    try:
        result = evaluate(args.task, data, args.answer.read_text(encoding="utf-8"))
        result["status"] = "VALID"
        if ref is not None:
            result["score_one_test"] = score(args.task, result["quality"], ref)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (InvalidAnswer, OSError) as exc:
        print(json.dumps({"status": "INVALID", "message": str(exc), "score_one_test": 0}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
