// 뷰어 공통 데이터 로더.
// 우선순위: ?data=<url> → ?data=local(끌어다 놓은 파일, IndexedDB) → data/graph_data.json → data/sample_graph.json
const KIND_ALIAS = {'절친': 'mutual', '짝사랑': 'oneway', '접점': 'weak'};  // 한글 kind 표기 호환
const DATA_PARAM = new URLSearchParams(location.search).get('data');

function normalizeGraph(d) {
  for (const l of d.links) l.kind = KIND_ALIAS[l.kind] || l.kind;
  d.meta = d.meta || {};
  d.meta.members = d.nodes.length;
  d.meta.links = d.links.length;
  if (d.meta.communities == null) d.meta.communities = new Set(d.nodes.map(n => n.community).filter(c => c >= 0)).size;
  return d;
}

function idb(mode, fn) {
  return new Promise((ok, no) => {
    const r = indexedDB.open('relation-viewer', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('g');
    r.onerror = () => no(r.error);
    r.onsuccess = () => {
      const tx = r.result.transaction('g', mode), q = fn(tx.objectStore('g'));
      tx.oncomplete = () => ok(q && q.result);
      tx.onerror = () => no(tx.error);
    };
  });
}

async function loadGraph() {
  if (DATA_PARAM === 'local') {
    try { const d = await idb('readonly', s => s.get('graph')); if (d) return normalizeGraph(d); } catch (e) {}
  }
  const urls = DATA_PARAM && DATA_PARAM !== 'local' ? [DATA_PARAM] : ['data/graph_data.json', 'data/sample_graph.json'];
  for (const u of urls) {
    try {
      const r = await fetch(u + (u.includes('?') ? '&' : '?') + 't=' + Date.now(), {cache: 'no-store'});
      if (r.ok) return normalizeGraph(await r.json());
    } catch (e) {}
  }
  return null;
}

// 다른 페이지로 넘어갈 때 같은 데이터 출처를 유지
function withData(url) {
  return DATA_PARAM ? url + (url.includes('?') ? '&' : '?') + 'data=' + encodeURIComponent(DATA_PARAM) : url;
}

// JSON 파일을 화면에 끌어다 놓거나 [데이터 열기] 로 고르면 그 데이터로 다시 연다
async function openGraphFile(file) {
  const d = JSON.parse(await file.text());
  if (!Array.isArray(d.nodes) || !Array.isArray(d.links)) { alert('nodes / links 가 있는 그래프 JSON 이 아닙니다'); return; }
  await idb('readwrite', s => s.put(d, 'graph'));
  location.href = location.pathname.replace(/[^/]*$/, 'index.html') + '?data=local';
}
function enableFileOpen(inputId) {
  document.addEventListener('dragover', e => e.preventDefault());
  document.addEventListener('drop', e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) openGraphFile(f); });
  const inp = document.getElementById(inputId);
  if (inp) inp.addEventListener('change', () => { if (inp.files[0]) openGraphFile(inp.files[0]); });
}
