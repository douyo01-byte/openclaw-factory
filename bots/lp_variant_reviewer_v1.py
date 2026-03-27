#!/usr/bin/env python3
import json
import os
import re
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def fetch_jobs(c, limit=10):
    return c.execute(
        """
        select *
        from conversation_jobs
        where coalesce(current_phase,'')='lp_variants_done'
          and coalesce(status,'')='done'
          and id not in (
            select job_id from conversation_artifacts where artifact_type='lp_review_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def get_lp_variants(c, job_id):
    return c.execute(
        """
        select id, artifact_title, artifact_body, version
        from conversation_artifacts
        where job_id=?
          and artifact_type='lp_markdown'
        order by version asc, id asc
        """,
        (job_id,),
    ).fetchall()

def score_variant(text: str):
    s = text or ""
    score = 50
    reasons = []

    if "ファーストビュー" in s:
        score += 10
        reasons.append("FVあり")
    if "こんな方へ" in s:
        score += 10
        reasons.append("対象明確")
    if "成分訴求" in s:
        score += 10
        reasons.append("成分訴求あり")
    if "CTA" in s:
        score += 10
        reasons.append("CTAあり")

    if "自然なツヤ" in s or "均一なトーン" in s:
        score += 5
        reasons.append("現サイト訴求反映")
    if "ヒト遺伝子組換オリゴペプチド-1" in s or "酢酸トコフェロール" in s:
        score += 5
        reasons.append("主要成分反映")

    if len(s) < 250:
        score -= 10
        reasons.append("情報量不足")
    if "まずは商品詳細をチェック" in s:
        reasons.append("CTA弱め")
        score -= 3

    score = max(0, min(100, score))
    return score, reasons

def build_review(job, variants):
    scored = []
    for v in variants:
        score, reasons = score_variant(v["artifact_body"])
        scored.append({
            "version": v["version"],
            "artifact_title": v["artifact_title"],
            "score": score,
            "reasons": reasons,
            "body": v["artifact_body"],
        })

    scored.sort(key=lambda x: (-x["score"], x["version"]))
    best = scored[0]

    lines = []
    lines.append(f"# LP3案レビュー job {job['id']}")
    lines.append("")
    for item in scored:
        lines.append(f"## {item['artifact_title']} | {item['score']}点")
        for r in item["reasons"]:
            lines.append(f"- {r}")
        lines.append("")
    lines.append("## 本命案")
    lines.append(f"- {best['artifact_title']}")
    lines.append(f"- 点数: {best['score']}")
    lines.append("")
    lines.append("## 改善方針")
    lines.append("- ファーストビューをもう一段強くする")
    lines.append("- CTAを商品詳細確認から購入導線寄りに強化する")
    lines.append("- 成分訴求とベネフィットの距離を縮める")
    lines.append("")
    lines.append("## 次アクション")
    lines.append(f"- improve_target: {best['artifact_title']}")
    lines.append("- improved_lpを1案生成")
    return "\n".join(lines), best

def save_review(c, job_id, body):
    c.execute(
        """
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
        """,
        (job_id, "lp_review_markdown", "lp_review", body, "", 1)
    )

def save_best(c, job_id, best):
    c.execute(
        """
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
        """,
        (
            job_id,
            "lp_best_markdown",
            "lp_best",
            best["body"],
            "",
            best["version"],
        )
    )
    c.execute(
        """
        update conversation_jobs
        set current_phase='lp_review_done',
            updated_at=datetime('now')
        where id=?
        """,
        (job_id,)
    )

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            variants = get_lp_variants(c, job["id"])
            if not variants:
                continue
            review_body, best = build_review(job, variants)
            save_review(c, job["id"], review_body)
            save_best(c, job["id"], best)
            print(f"reviewed job_id={job['id']} best={best['artifact_title']} score={best['score']}", flush=True)
            done += 1
        except Exception as e:
            print(f"error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"review_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
