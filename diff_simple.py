#!/usr/bin/env python3
import sys, ast, subprocess, csv
from collections import Counter

def run(cmd):
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if p.returncode:
        sys.exit(f"Error running `{cmd}`:\n{p.stderr}")
    return p.stdout

def load_version(branch, path):
    return run(f"git show {branch}:{path}")

def extract_defs(src):
    tree = ast.parse(src)
    defs = {}
    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            # collect name, start, end, body
            start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
            body_lines = []
            for s in node.body:
                if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                    continue
                try:
                    body_lines.append(ast.unparse(s).strip())
                except:
                    pass
            code = "\n".join(body_lines)
            defs[node.name] = (start, end, code)
            self.generic_visit(node)
        def visit_ClassDef(self, node):
            self.generic_visit(node)
    V().visit(tree)
    return defs

def blame_author(branch, path, a, b):
    out = run(f"git blame {branch} -L{a},{b} --porcelain -- {path}")
    authors = [L.split(" ",1)[1] for L in out.splitlines() if L.startswith("author ")]
    return Counter(authors).most_common(1)[0][0] if authors else "UNKNOWN"

if __name__=="__main__":
    if len(sys.argv)!=4:
        sys.exit("Usage: diff_simple.py <file> <old_branch> <new_branch>")

    path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]

    old_src = load_version(old, path)
    new_src = load_version(new, path)

    old_defs = extract_defs(old_src)
    new_defs = extract_defs(new_src)

    added   = set(new_defs) - set(old_defs)
    removed = set(old_defs) - set(new_defs)
    common  = set(old_defs) & set(new_defs)
    updated = {f for f in common if old_defs[f][2] != new_defs[f][2]}

    # function_changes.csv (new & updated)
    with open("function_changes.csv", "w", newline="") as f1:
        writer = csv.writer(f1)
        writer.writerow(["function", "status", "author"])
        for fn in sorted(added):
            a, b, _ = new_defs[fn]
            author = blame_author(new, path, a, b)
            writer.writerow([fn, "new", author])
        for fn in sorted(updated):
            a, b, _ = new_defs[fn]
            author = blame_author(new, path, a, b)
            writer.writerow([fn, "updated", author])

    # removed_functions.csv (removed only)
    with open("removed_functions.csv", "w", newline="") as f2:
        writer = csv.writer(f2)
        writer.writerow(["function", "author"])
        for fn in sorted(removed):
            a, b, _ = old_defs[fn]
            author = blame_author(old, path, a, b)
            writer.writerow([fn, author])

    print("✅ Wrote function_changes.csv and removed_functions.csv")
