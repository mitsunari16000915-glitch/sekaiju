// index.html の DATA（7クラスター・35サブ要素・250課題）から課題一覧を書き出す
// 使い方: node tools/news/problems.js index.html 出力.json
const fs = require('fs');
const [html, out] = process.argv.slice(2);
const src = fs.readFileSync(html, 'utf8');
const s = src.indexOf('const DATA = [');
const e = src.indexOf('\n];', s);
if (s < 0 || e < 0) throw new Error('index.html に const DATA が見つかりません');
const DATA = eval(src.slice(s + 'const DATA = '.length, e + 2));
const list = [];
DATA.forEach((c, ci) => c.subs.forEach(sb => {
  const probs = Object.values(sb).find(v => Array.isArray(v) && Array.isArray(v[0])) || [];
  probs.forEach(p => list.push({ cluster: ci + 1, cname: c.name, sub: sb.id, sname: sb.n, name: p[0], desc: p[1] }));
}));
fs.writeFileSync(out, JSON.stringify(list, null, 1));
console.log(`課題 ${list.length} 件（クラスター ${DATA.length}・サブ要素 ${DATA.reduce((a, c) => a + c.subs.length, 0)}）`);
