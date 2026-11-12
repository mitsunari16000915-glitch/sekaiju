// 250課題ごとに Bing ニュース RSS を引き、SINCE 以降の記事候補を集める（既存URLは除外）
// 使い方: node collect.js problems.json news.json SINCE(YYYY-MM-DD) out.json
const fs=require('fs');const {execFileSync}=require('child_process');
const [P,N,SINCE,OUT]=process.argv.slice(2);
const probs=JSON.parse(fs.readFileSync(P));const news=JSON.parse(fs.readFileSync(N)).items;
const norm=u=>u.replace(/^https?:\/\//,'').replace(/^www\./,'').replace(/[?#].*$/,'').replace(/\/$/,'');
const have=new Set(news.map(x=>norm(x.url)));
const SKIP=/(prtimes\.jp|atpress\.ne\.jp|value-press|dreamnews|newscast\.jp|kyodonewsprwire|youtube\.com|x\.com|twitter\.com|facebook\.com|note\.com|ameblo|livedoor\.blog|hatenablog|news\.goo\.ne\.jp|msn\.com|smartnews|gunosy|antenna|newspicks)/;
const dec=s=>s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/<[^>]+>/g,'');
const q=n=>n.replace(/[「」『』（）()]/g,' ').replace(/[0-9０-９,.%％万千億人件位年]+/g,' ').replace(/\s+/g,' ').trim();
const out=[];const seen=new Set();let i=0;
for(const p of probs){i++;
  const url='https://www.bing.com/news/search?format=rss&setlang=ja&cc=JP&mkt=ja-JP&qft=sortbydate%3d%221%22&q='+encodeURIComponent(q(p.name));
  let xml='';try{xml=execFileSync('curl',['-sS','--max-time','25',url],{encoding:'utf8'});}catch(e){continue;}
  for(const it of xml.split('<item>').slice(1)){
    const g=t=>{const m=it.match(new RegExp('<'+t+'>([\\s\\S]*?)</'+t+'>'));return m?m[1]:''};
    const link=dec(g('link'));const m=link.match(/[?&]url=([^&]+)/);if(!m)continue;
    const u=decodeURIComponent(m[1]);const d=new Date(g('pubDate'));if(isNaN(d)||d.toISOString().slice(0,10)<SINCE)continue;
    if(SKIP.test(u)||have.has(norm(u))||seen.has(norm(u)+'|'+p.name))continue;seen.add(norm(u)+'|'+p.name);
    out.push({problem:p.name,cluster:p.cluster,sub:p.sub,title:dec(g('title')),desc:dec(g('description')).slice(0,300),url:u,source:dec(g('News:Source')),date:d.toISOString().slice(0,10)});
  }
  if(i%25===0)process.stderr.write(`  ${i}/${probs.length} 課題 … 候補 ${out.length}\n`);
  execFileSync('sleep',['0.4']);
}
fs.writeFileSync(OUT,JSON.stringify(out,null,1));
const byC={};out.forEach(x=>byC['c'+x.cluster]=(byC['c'+x.cluster]||0)+1);
console.log('候補',out.length,'件 / URL重複除く',new Set(out.map(x=>norm(x.url))).size,'件',JSON.stringify(byC));
