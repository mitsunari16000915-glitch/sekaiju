// 候補（collect.js の出力）を、信頼できる報道機関・官公庁かつ見出しに課題語を含むものに絞り、一覧を表示する
// 使い方: node tools/news/shortlist.js 候補.json 絞込.json > 一覧.txt
const fs=require('fs');const C=JSON.parse(fs.readFileSync(process.argv[2]));
const TRUST=/(\.go\.jp$|^(asahi\.com|nikkei\.com|mainichi\.jp|yomiuri\.co\.jp|sankei\.com|nishinippon\.co\.jp|news\.web\.nhk|47news\.jp|kobe-np\.co\.jp|tokyo-np\.co\.jp|hokkaido-np\.co\.jp|kyoto-np\.co\.jp|reuters\.com|afpbb\.com|fukuishimbun\.co\.jp|sanyonews\.jp|saga-s\.co\.jp|toonippo\.co\.jp|sakigake\.jp|chunichi\.co\.jp|okinawatimes\.co\.jp|kyodo\.co\.jp|nippon\.com|hokkoku\.co\.jp|shikoku-np\.co\.jp|agara\.co\.jp|shinmai\.co\.jp|jiji\.com|fnn\.jp|news\.ntv\.co\.jp|newsdig\.tbs\.co\.jp|toyokeizai\.net|kyobun\.co\.jp|kumanichi\.com|ryukyushimpo\.jp|nnn\.co\.jp|business\.nikkei\.com|itmedia\.co\.jp|nikkei\.com|tdb\.co\.jp|tsr-net\.co\.jp|factcheckcenter\.jp|jil\.go\.jp))$/;
const host=u=>new URL(u).hostname.replace(/^www\./,'');
const toks=n=>n.replace(/[「」『』（）()・、の]/g,' ').split(/\s+/).filter(t=>t.length>=2);
const rel=x=>{const t=x.title+x.desc;return toks(x.problem).filter(k=>t.includes(k)).length;};
const S=C.filter(x=>TRUST.test(host(x.url))).map(x=>({...x,h:host(x.url),r:rel(x)})).filter(x=>x.r>0);
const byU=new Map();S.forEach(x=>{const k=x.url;if(!byU.has(k)||byU.get(k).r<x.r)byU.set(k,x)});
const L=[...byU.values()].sort((a,b)=>a.cluster-b.cluster||a.problem.localeCompare(b.problem)||b.date.localeCompare(a.date));
L.forEach((x,i)=>x.k=i+1);fs.writeFileSync(process.argv[3],JSON.stringify(L,null,1));
let cur=0;for(const x of L){if(x.cluster!==cur){cur=x.cluster;console.log(`\n##### c${cur}`);}console.log(`${x.k}\t${x.problem}\t${x.date.slice(5)}\t${x.h}\t${x.title.slice(0,70)}`);}
console.log('\n計',L.length,'件');
