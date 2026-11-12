// 選別済みの新しいニュースを news.json に追記マージする
// 使い方: node tools/news/merge.js news.json 新規.json 課題一覧.json 初出日(YYYY-MM-DD) [--dry]
//
// - 必須項目・課題名（index.html の250課題）・クラスター・status/kind を検査する
// - URL を正規化して既存と重複するものは除外する
// - URL に実際に届くか確かめる（2xx=verified:true／政府系の403等=“blocked”／それ以外は除外）
// - id は "n" + URL の32bitハッシュ（Java式）の36進表記（既存の約半数と同じ方式。重複時は末尾に x を足す）
// - 末尾に追記し、generated・counts・note の件数と日付を更新する
// - 書式は従来どおり 1行の JSON（末尾改行なし）
const fs = require('fs');
const { execFileSync } = require('child_process');
const [NEWS, NEWITEMS, PROBS, DAY] = process.argv.slice(2);
const DRY = process.argv.includes('--dry');
if (!/^\d{4}-\d{2}-\d{2}$/.test(DAY || '')) throw new Error('初出日を YYYY-MM-DD で指定してください');

const j = JSON.parse(fs.readFileSync(NEWS, 'utf8'));
const add = JSON.parse(fs.readFileSync(NEWITEMS, 'utf8'));
const probs = new Map(JSON.parse(fs.readFileSync(PROBS, 'utf8')).map(p => [p.name, p.cluster]));
const KEYS = ['id', 'title', 'summary', 'url', 'source', 'date', 'problems', 'cluster', 'status', 'kind', 'reason', 'verified', 'first_seen'];
const norm = u => u.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/[?#].*$/, '').replace(/\/$/, '');
const hash = s => { let h = 0; for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); };
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';
const reach = u => {
  try { return execFileSync('curl', ['-sS', '-L', '--max-time', '30', '-A', UA, '-o', '/dev/null', '-w', '%{http_code}', u], { encoding: 'utf8' }).trim(); }
  catch (e) { return '000'; }
};

const have = new Set(j.items.map(x => norm(x.url)));
const ids = new Set(j.items.map(x => x.id));
const ok = [], ng = [];
for (const x of add) {
  const why = [];
  for (const k of ['title', 'summary', 'url', 'source', 'date', 'reason']) if (!x[k] || typeof x[k] !== 'string') why.push(`${k} が空`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(x.date || '')) why.push('date の形式');
  if (!Array.isArray(x.problems) || !x.problems.length) why.push('problems が空');
  else for (const p of x.problems) if (!probs.has(p)) why.push(`課題名が無い: ${p}`);
  if (!(x.cluster >= 1 && x.cluster <= 7)) why.push('cluster は1〜7');
  if (!['adopted', 'pending'].includes(x.status)) why.push('status は adopted / pending');
  if (!['evidence', 'progress'].includes(x.kind)) why.push('kind は evidence / progress');
  if (have.has(norm(x.url || ''))) why.push('既存と同じURL');
  if (why.length) { ng.push([x.title, why.join('・')]); continue; }
  const code = reach(x.url);
  let verified;
  if (/^2/.test(code)) verified = true;
  else if (/\.go\.jp\//.test(x.url) && /^(403|401|429|000)$/.test(code)) verified = 'blocked';
  else { ng.push([x.title, `URLに届かない（HTTP ${code}）`]); continue; }
  let id = 'n' + hash(x.url); while (ids.has(id)) id += 'x';
  ids.add(id); have.add(norm(x.url));
  const item = { ...x, id, verified, first_seen: DAY };
  ok.push(Object.fromEntries(KEYS.map(k => [k, item[k]])));
}

j.items.push(...ok);
const a = j.items, n = f => a.filter(f).length;
j.generated = DAY;
j.counts = { total: a.length, adopted: n(x => x.status === 'adopted'), pending: n(x => x.status === 'pending'),
             evidence: n(x => x.kind === 'evidence'), progress: n(x => x.kind === 'progress') };
j.note = j.note.replace(/\d{4}-\d{2}-\d{2}時点で累計\d+件/, `${DAY}時点で累計${a.length}件`);

console.log(`追加 ${ok.length} 件（採用 ${ok.filter(x => x.status === 'adopted').length}・要判断 ${ok.filter(x => x.status === 'pending').length}／evidence ${ok.filter(x => x.kind === 'evidence').length}・progress ${ok.filter(x => x.kind === 'progress').length}／blocked ${ok.filter(x => x.verified === 'blocked').length}）`);
const byC = {}; ok.forEach(x => byC['c' + x.cluster] = (byC['c' + x.cluster] || 0) + 1); console.log('クラスター別', JSON.stringify(byC));
if (ng.length) { console.log(`除外 ${ng.length} 件:`); ng.forEach(([t, w]) => console.log(`  - ${t.slice(0, 40)} … ${w}`)); }
console.log(`累計 ${a.length} 件 counts=${JSON.stringify(j.counts)}`);
if (!DRY) { fs.writeFileSync(NEWS, JSON.stringify(j)); console.log(`${NEWS} を更新しました`); } else console.log('（--dry: 書き込みなし）');
