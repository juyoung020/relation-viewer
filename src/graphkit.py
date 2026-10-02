"""상호작용 가중치 → 관계망 JSON (뷰어 입력 형식).

데이터 출처와 무관한 핵심 로직. 수집기(CSV 변환기, 각 서비스용 크롤러 등)는
"누가 누구에게 얼마나" 를 모아 build_graph() 에 넘기기만 하면 된다.

입력
  directed   : {(a, b): w}   a → b 방향 상호작용 가중치 (댓글·멘션·답장 등)
  undirected : {(a, b): w}   방향 없는 접점 가중치 (같은 글에 함께 댓글 등), 선택
  names      : {id: 표시 이름}, 선택
  me         : 내 노드 id, 선택 (뷰어에서 '(나)' 로 표시)

관계 판정
  양쪽 방향 모두 MUTUAL_MIN 이상 → mutual (상호)
  한쪽만 TAU 이상             → oneway (일방, 방향 보존)
  그 외 합계만 TAU 이상         → weak (약한 접점)
노드 지표: 가중 연결도 기반 중심성(0~1) → 영향력 순위, Louvain 커뮤니티.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import networkx as nx

try:
    import community as community_louvain  # python-louvain
except Exception:
    community_louvain = None

DEFAULTS = dict(
    TAU=1.5,          # 이 미만 누적 가중치 관계는 버림
    MUTUAL_MIN=1.5,   # 양방향 최솟값이 이 이상이면 mutual
    TOPK_EDGES=18,    # 노드당 강한 관계 상위 N개만 유지 (허브 폭발 방지)
    MIN_DEGREE=2,     # 연결이 이보다 적은 잎 노드 제거
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "viewer" / "data" / "graph_data.json"


def build_graph(directed, undirected=None, names=None, me=None, keep=None, extra=None, **params):
    """keep: 연결이 적어도 항상 남길 노드 id 집합. extra: {id: {추가 필드}} (예: tier, img)."""
    p = {**DEFAULTS, **params}
    undirected = undirected or {}
    names = names or {}
    extra = extra or {}
    keep = set(keep or ())

    def pk(a, b):
        return tuple(sorted((a, b)))

    pairs = {}
    for a, b in {pk(a, b) for (a, b) in directed} | {pk(a, b) for (a, b) in undirected}:
        ab, ba = directed.get((a, b), 0.0), directed.get((b, a), 0.0)
        total = ab + ba + undirected.get((a, b), 0.0) + undirected.get((b, a), 0.0)
        if total < p["TAU"]:
            continue
        if min(ab, ba) >= p["MUTUAL_MIN"]:
            kind, direction = "mutual", None
        elif max(ab, ba) >= p["TAU"]:
            kind, direction = "oneway", ((a, b) if ab >= ba else (b, a))
        else:
            kind, direction = "weak", None
        pairs[(a, b)] = {"weight": round(total, 2), "kind": kind, "dir": direction}

    # 노드당 top-k 가지치기
    inc = collections.defaultdict(list)
    for key, info in pairs.items():
        inc[key[0]].append((info["weight"], key))
        inc[key[1]].append((info["weight"], key))
    kept = {key for lst in inc.values() for _, key in sorted(lst, reverse=True)[:p["TOPK_EDGES"]]}
    pairs = {k: v for k, v in pairs.items() if k in kept}

    G = nx.Graph()
    for (a, b), info in pairs.items():
        G.add_edge(a, b, weight=info["weight"])
    alive = {n for n in G.nodes if G.degree(n) >= p["MIN_DEGREE"]} | (keep & set(G.nodes))
    if me in G:
        alive.add(me)
    G = G.subgraph(alive).copy()
    pairs = {k: v for k, v in pairs.items() if k[0] in alive and k[1] in alive}

    comm = {}
    if community_louvain and G.number_of_edges():
        comm = community_louvain.best_partition(G, weight="weight", random_state=42)
    wdeg = {n: sum(d["weight"] for _, _, d in G.edges(n, data=True)) for n in G.nodes}
    mx = max(wdeg.values()) if wdeg else 1.0
    cent = {n: (v / mx if mx else 0) for n, v in wdeg.items()}
    ranked = sorted(G.nodes, key=lambda n: cent.get(n, 0), reverse=True)
    rank_of = {n: i + 1 for i, n in enumerate(ranked)}

    nodes = []
    for n in G.nodes:
        nodes.append({
            "id": n,
            "name": names.get(n) or str(n),
            "is_me": n == me,
            "community": comm.get(n, -1),
            "centrality": round(cent.get(n, 0), 5),
            "rank": rank_of.get(n),
            "size": round(6 + 60 * cent.get(n, 0), 1),
            **extra.get(n, {}),
        })
    links = []
    for (a, b), info in pairs.items():
        src, dst = info["dir"] if info["dir"] else (a, b)
        links.append({"source": src, "target": dst, "weight": info["weight"],
                      "kind": info["kind"], "directed": info["kind"] == "oneway"})

    return {"nodes": nodes, "links": links,
            "meta": {"members": len(nodes), "links": len(links),
                     "communities": len(set(comm.values())) if comm else 0}}


def write(graph, path=DEFAULT_OUT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    return path
