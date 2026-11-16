# 世界樹ニュースの週次蓄積 — 手順書

`news.json` に、250課題のエビデンスとなるニュースを毎週追記する作業の手順です。
2026年11月にクラウド（Claude Code）での自動実行に移行した際、それまでPCで行っていた作業を
過去のデータから読み解いて文書化しました。人が行う場合も、自動実行のClaudeが行う場合も、この手順に従います。

## 前提

- 作業日は日本時間（`TZ=Asia/Tokyo date +%F`）。これを `first_seen`（初出日）と `generated` に使う。
- 収集の対象期間は「前回の `generated` の日」以降に公開された記事。
- `news.json` は **1行のJSON（末尾改行なし）**。手で整形しない（`merge.js` が書き出す）。
- 既存の記事（過去の項目）は書き換えない。追記のみ。`status` を `rejected` などに変えるのは鈴木様の管理画面の仕事。

## 項目の書き方（1件分）

| 項目 | 書き方 |
|---|---|
| `title` | 記事の見出しをもとに、事実と数値が一目で分かる一文に書き直す |
| `summary` | **記事本文で確認できた事実だけ**で書く。日付・主体・数値を入れて100〜200字程度。推測や評価を混ぜない |
| `url` | 元記事のURL（転載サイトより発信元を優先。計測用のクエリ `utm_` などは付けない。時事通信の `article?k=…` のようにクエリで記事を見分けるサイトはそのまま） |
| `source` | 媒体名。共同通信の配信記事は「熊本日日新聞（共同通信配信）」のように書く |
| `date` | 記事の公開日 |
| `problems` | 関係する課題名。`index.html` の250課題の名前と**完全一致**させる（1〜2件） |
| `cluster` | 1件目の課題のクラスター番号（1〜7） |
| `kind` | `evidence`＝課題が起きている・悪化している証拠／`progress`＝解決に向けた前進 |
| `status` | `adopted`＝出典が確かで課題との結びつきが明確／`pending`＝結びつきが曖昧・一次資料を確認できない等（鈴木様が判定） |
| `reason` | 採用または要判断とした理由を一文で。要判断なら何が足りないかを書く |

`id`・`verified`・`first_seen` は `merge.js` が付ける。

## 手順

```bash
DAY=$(TZ=Asia/Tokyo date +%F)
SINCE=$(node -e 'console.log(JSON.parse(require("fs").readFileSync("news.json","utf8")).generated)')
W=$(mktemp -d)

# 1. 課題一覧（250件）を index.html から取り出す
node tools/news/problems.js index.html $W/problems.json

# 2. 全課題についてニュース検索（Bing ニュースRSS）し、SINCE 以降の候補を集める（既存URLは除外）
node tools/news/collect.js $W/problems.json news.json $SINCE $W/candidates.json

# 3. 信頼できる報道機関・官公庁＋見出しに課題語を含むものに絞って一覧化
node tools/news/shortlist.js $W/candidates.json $W/shortlist.json > $W/shortlist.txt
```

4. **選別**（ここはClaudeが読んで判断する）
   - 一覧から、数値や具体的な施策を含む記事を選ぶ。目安は **20〜60件**、7クラスターに偏りすぎないように。
   - 採用ニュースが0件の課題を優先して探す（一覧に無ければ `candidates.json` 全体も見る）。
   - 除外するもの: 企業のプレスリリース・宣伝記事（例 `asahi.com/and/pressrelease`）、まとめサイト、イベント告知だけの記事、論評・社説（事実の報道を優先）。
   - **既に登録済みの出来事は入れない**。`news.json` の `title`・`summary` をキーワードで検索して確かめる（URLが違っても同じ統計・同じ発表なら重複）。
5. 選んだ記事を1件ずつ取得して本文を読み、上の表のとおり書き起こして `$W/new_items.json`（配列）に保存する。
   本文が有料で読めない記事は、読める範囲（リード文）の事実だけで書く。
6. 追記（必須項目・課題名・重複・URL到達を検査してから書き込む）

```bash
node tools/news/merge.js news.json $W/new_items.json $W/problems.json $DAY --dry   # 試し
node tools/news/merge.js news.json $W/new_items.json $W/problems.json $DAY         # 本番
```

7. 確認: `index.html` をローカルで開き、`NEWS.loaded` が真で、`NEWS.freshDate` が今日になっていること。
8. コミットして `main` に push する。メッセージは従来の書式:

```
chore: 世界樹ニュース自動蓄積（週次）＝+追加件数件・累計総件数件／ブレ+N件
```

## 未来知のブレ（revisions.json）

収集中に、世界樹の仮説や数値（`index.html` のサブ要素の仮説文・課題の数値）を**明確に覆す・更新する**一次資料に当たった場合だけ、
`revisions.json` に `applied: false`（鈴木様の判断待ち）で追記する。書式は既存の項目に合わせる
（`id`・`scope`=sub/problem・`key`・`date`・`kind`=仮説の反証/数値更新/定義の要確認・`headline`・`before`・`finding`・`after`・`applied`・`sources`）。
本体（`index.html`）は書き換えない。該当がなければ「ブレ+0件」。

## 公開について

GitHub の `main` に入れただけでは公開サイト（sengokudama.com/sekaiju/）は変わらない。
公開サイトへの送信（FTP）は鈴木様のPCから行う。クラウド環境からはFTPの窓口に接続できない。
