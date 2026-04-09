#!/usr/bin/env python3
import os
import sqlite3
import sys

DB_PATH = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    try:
        con.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return con

def artifact_map(c, job_id: int):
    rows = c.execute("""
        select artifact_type, artifact_title, artifact_body, coalesce(artifact_path,'') as artifact_path, coalesce(version,1) as version
        from conversation_artifacts
        where job_id=?
        order by id asc
    """, (job_id,)).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["artifact_type"], []).append(r)
    return out

def latest_body(arts, key: str) -> str:
    arr = arts.get(key) or []
    return arr[-1]["artifact_body"] if arr else ""

def load_reference_patterns(c):
    rows = c.execute("""
        select job_id, artifact_body
        from conversation_artifacts
        where artifact_type='reference_lp_pattern'
          and job_id in (20,21)
        order by job_id asc
    """).fetchall()
    return "\n\n".join([r["artifact_body"] for r in rows])

def save_artifact(c, job_id: int, artifact_type: str, artifact_title: str, body: str, version: int = 1):
    c.execute("""
        insert into conversation_artifacts(
            job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
    """, (job_id, artifact_type, artifact_title, body, "", version))

def build_rebuild(job, arts, reference_text: str) -> str:
    analysis = latest_body(arts, "analysis_markdown")
    lp_review = latest_body(arts, "lp_review_markdown")
    lp_improved = latest_body(arts, "lp_improved_markdown")
    fv = latest_body(arts, "fv_copy_final_markdown")
    cta = latest_body(arts, "cta_compare_markdown")
    section_outline = latest_body(arts, "section_outline_markdown")
    section_body = latest_body(arts, "section_body_markdown")

    return f"""# {job['target_object']} 再設計方針 v2

## 結論
現状LPは「情報整理」はできているが、
- 悩みの刺し込みが弱い
- ベネフィットの情緒が弱い
- 視覚主導の設計に寄り切れていない
- CTAが無難すぎて購買の後押しが弱い

そのため、参考LP群の共通点をもとに、educate B は以下へ寄せる。
1. FVで悩み→仕上がり価値を即伝達
2. 商品画像を主役にした余白多め構成
3. 1セクション1メッセージで縦に流す
4. CTAを「説明」から「行動」へ寄せる

## reference学習要約
{reference_text[:5000]}

## 現状LPの弱点
### 1. 悩み訴求の弱さ
現状は「整えて魅せる」という表現はあるが、
誰のどんな悩みに刺さるのかが弱い。
最初の1画面で
- 厚塗りしたくない
- 肌印象は整えたい
- 乾燥感は避けたい
を明示する必要がある。

### 2. 成分と価値の距離
成分名はあるが、「だからどう嬉しいか」が弱い。
セラミド、水添レシチン、植物オイル類は
“しっとり感”“つっぱりにくさ”“心地よいベース作り”
へ翻訳して見せるべき。

### 3. デザイン前提の文量調整不足
現状は文章が均一で、視覚強弱が弱い。
参考LP群のように
- 短い大見出し
- 1行ベネフィット
- 要点3つ
- 行動CTA
へ圧縮する。

## 再設計コンセプト
### コンセプト名
素肌を隠すのではなく、印象を整えるBB下地

### トーン
- 上質感
- 清潔感
- 誇張しすぎない
- 女性向け美容商材らしい軽やかさ
- 情報を詰めすぎず、画像と余白で見せる

## 再設計FV案
### メインコピー
厚塗り感は出したくない。  
でも、肌印象はきれいに整えたい。

### サブコピー
自然なツヤ、均一なトーン、しっとり感を意識した、
毎日使いやすいBB下地。

### ベネフィット3点
- 厚塗り感を抑えて肌印象を整える
- 乾燥感を避けながら心地よく使える
- ベースメイク時間を上質なケア発想へ

### CTA再設計
- まずは商品詳細を見る
- educate B の魅力を確認する
- 自分の肌印象を整える一歩を始める

## 再設計セクション順
1. 悩み直撃FV
2. こんな方へ
3. 仕上がり価値
4. 成分発想と心地よさ
5. 使用イメージ
6. 商品画像＋要点整理
7. CTA

## セクションごとの改善要点
### 1. FV
コピー量を減らす。悩み→価値→CTAだけに絞る。

### 2. こんな方へ
箇条書き3つまで。
- 厚塗りしたくない
- 肌印象を自然に整えたい
- 乾燥感を避けたい

### 3. 仕上がり価値
「自然なツヤ」「均一なトーン」「しっとり感」を3カードで見せる。

### 4. 成分発想
成分名羅列ではなく、
- セラミド系
- 植物オイル系
- 美容発想成分
の3群にまとめる。

### 5. 使用イメージ
顔アップ、手元、テクスチャ、日常シーン。
“塗る”より“印象が整う”絵を優先。

### 6. 商品要約
パッケージ画像横に
- 商品名
- 仕上がりキーワード
- 使いやすさ
- CTA
を置く。

### 7. CTA
終盤CTAは行動型に寄せる。
無難さより一歩進ませる言い回しにする。

## 現成果物から活かすもの
### analysis
{analysis[:1200]}

### lp_review
{lp_review[:1200]}

### lp_improved
{lp_improved[:1200]}

### fv_copy_final
{fv[:1200]}

### cta_compare
{cta[:1200]}

### section_outline
{section_outline[:1200]}

### section_body
{section_body[:1200]}

## 次に作るべきもの
1. reference反映版 FVコピー
2. reference反映版 section outline
3. reference反映版 section body
4. reference反映版 final LP
5. reference反映版 HTML

## 判定
今のLPは「あと10%で売れる」段階ではなく、
構成・訴求・デザイン前提の言葉選びを大きく寄せ直す必要がある。
体感として 60〜70% 再設計が必要、という判断は妥当。
"""
def run_once(job_id: int):
    con = connect()
    c = con.cursor()
    job = c.execute("""
        select id, target_object, request_text, current_phase, status
        from conversation_jobs
        where id=?
    """, (job_id,)).fetchone()
    if not job:
        raise SystemExit("job_not_found")
    arts = artifact_map(c, job_id)
    reference_text = load_reference_patterns(c)
    body = build_rebuild(job, arts, reference_text)
    save_artifact(c, job_id, "reference_lp_apply_markdown", "reference_lp_apply", body, 1)
    c.execute("""
        update conversation_jobs
        set current_phase='reference_lp_apply_done',
            updated_at=datetime('now')
        where id=?
    """, (job_id,))
    con.commit()
    con.close()
    print(f"reference_apply_done job_id={job_id}", flush=True)

def main():
    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    run_once(job_id)

if __name__ == "__main__":
    main()
