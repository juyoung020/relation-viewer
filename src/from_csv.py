"""CSV 상호작용 기록 → 뷰어용 graph_data.json.

어떤 서비스든 "누가 누구에게" 기록만 있으면 된다 (메신저 답장, 커뮤니티 댓글, 협업 멘션 등).

interactions.csv (헤더 필수)
  source,target[,weight][,type]
  - weight 생략 시 1. 같은 쌍이 여러 줄이면 합산.
  - type 이 'undirected' 면 방향 없는 접점(예: 같은 스레드 참여), 기본은 directed.
nodes.csv (선택)
  id,name

실행:
  python src/from_csv.py examples/sample_interactions.csv --nodes examples/sample_nodes.csv --me u001
"""
from __future__ import annotations

import argparse
import collections
import csv

import graphkit


def read(path, nodes_path=None):
    directed = collections.defaultdict(float)
    undirected = collections.defaultdict(float)
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            a, b = r["source"].strip(), r["target"].strip()
            if not a or not b or a == b:
                continue
            w = float(r.get("weight") or 1)
            if (r.get("type") or "").strip().lower() == "undirected":
                undirected[tuple(sorted((a, b)))] += w
            else:
                directed[(a, b)] += w
    names = {}
    if nodes_path:
        with open(nodes_path, encoding="utf-8-sig", newline="") as f:
            names = {r["id"].strip(): r["name"].strip() for r in csv.DictReader(f)}
    return dict(directed), dict(undirected), names


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("interactions")
    ap.add_argument("--nodes")
    ap.add_argument("--me", help="내 노드 id (뷰어에 '(나)' 표시)")
    ap.add_argument("--out", default=str(graphkit.DEFAULT_OUT))
    ap.add_argument("--min-degree", type=int, default=graphkit.DEFAULTS["MIN_DEGREE"])
    a = ap.parse_args()
    directed, undirected, names = read(a.interactions, a.nodes)
    g = graphkit.build_graph(directed, undirected, names, me=a.me, MIN_DEGREE=a.min_degree)
    path = graphkit.write(g, a.out)
    m = g["meta"]
    print(f"nodes={m['members']} links={m['links']} communities={m['communities']} → {path}")


if __name__ == "__main__":
    main()
