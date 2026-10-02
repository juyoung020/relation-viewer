"""가상 커뮤니티 상호작용 데이터 생성 (실제 인물 없음).

몇 개의 무리(커뮤니티) 안에서 활동량이 거듭제곱 분포를 따르는 사람들이 서로 댓글을 주고받는다고 가정한다.
결과: examples/sample_interactions.csv, examples/sample_nodes.csv
그다음 src/from_csv.py 로 viewer/data/sample_graph.json 을 만든다.

실행: python examples/make_sample.py
"""
import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
random.seed(7)

N, GROUPS, EVENTS = 420, 7, 26000
A = "가나다라마바사아자차카타파하"
B = "람솔윤린별결빛온담솜율슬하늘봄찬새"


def nick(i):
    return random.choice(A) + random.choice(B) + random.choice(["", "", "이", "님", "_" + str(i % 97)])


people = [f"u{i:03d}" for i in range(N)]
names, used = {}, set()
for i, p in enumerate(people):
    n = nick(i)
    while n in used:
        n = nick(i + random.randint(1, 999))
    used.add(n)
    names[p] = n
group = {p: random.randrange(GROUPS) for p in people}
activity = {p: random.paretovariate(1.3) for p in people}   # 소수가 대부분의 활동
by_group = {g: [p for p in people if group[p] == g] for g in range(GROUPS)}
weights = list(activity.values())

rows = []
for _ in range(EVENTS):
    a = random.choices(people, weights)[0]
    pool = by_group[group[a]] if random.random() < 0.82 else people          # 대부분 같은 무리 안
    b = random.choices(pool, [activity[x] for x in pool])[0]
    if a == b:
        continue
    kind = random.random()
    if kind < 0.6:
        rows.append((a, b, 1, "directed"))          # 댓글
    elif kind < 0.8:
        rows.append((a, b, 3, "directed"))          # 멘션
    else:
        rows.append((a, b, 0.5, "undirected"))      # 같은 글에 함께 댓글
# 상위 몇 명은 서로 자주 주고받는 단짝 관계
top = sorted(people, key=activity.get, reverse=True)[:12]
for x, y in zip(top[::2], top[1::2]):
    for _ in range(60):
        rows.append((x, y, 1, "directed"))
        rows.append((y, x, 1, "directed"))

with open(HERE / "sample_interactions.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["source", "target", "weight", "type"])
    w.writerows(rows)
with open(HERE / "sample_nodes.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "name"])
    w.writerows(names.items())
print(f"{len(rows)} interactions, {N} people → {HERE}")
