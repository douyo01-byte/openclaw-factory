from __future__ import annotations
from datetime import datetime, timezone
import json
import os
import re
import sqlite3
import subprocess
import urllib.parse
import urllib.request

DB_PATH = os.environ.get("OCLAW_DB_PATH", "/Users/doyopc/AI/openclaw-factory/data/openclaw.db")
BASE_BRANCH = "main"
REPO = "/Users/doyopc/AI/openclaw-factory"
KAI_LOG = os.path.join(REPO, "logs", "kai_actions.log")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sh(args, capture=False):
    env = dict(os.environ)
    env["HOME"] = "/Users/doyopc"
    env["PATH"] = "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    if capture:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=REPO,
            env=env,
        )
        return p.stdout.strip()
    subprocess.run(args, cwd=REPO, env=env, check=True)

def kai(conn, pid, event, **kw):
    os.makedirs(os.path.dirname(KAI_LOG), exist_ok=True)
    payload = {"ts": now(), "proposal_id": pid, "event": event, **kw}
    with open(KAI_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    conn.execute(
        "INSERT INTO dev_events (proposal_id,event_type,payload) VALUES (?,?,?)",
        (pid, event, json.dumps(payload, ensure_ascii=False)),
    )
    tok = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TG_BOT_TOKEN") or ""
    chat = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TG_CHAT_ID") or ""
    if tok and chat:
        data = urllib.parse.urlencode(
            {
                "chat_id": chat,
                "text": ("Kai: %s pid=%s " % (event, pid)) + " ".join([("%s=%s" % (k, v)) for k, v in kw.items()]),
            }
        ).encode("utf-8")
        urllib.request.urlopen(
            "https://api.telegram.org/bot%s/sendMessage" % tok, data=data, timeout=10
        ).read()

def parse_business_task(spec: str):
    meta = {}
    for line in (spec or "").splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        meta[k.strip()] = v.strip()
    return meta

def render_business_output(title: str, spec: str):
    meta = parse_business_task(spec)
    task_type = (meta.get("task_type") or "").strip()
    theme = (meta.get("theme") or "").strip()

    if task_type == "lp_generation":
        return (
            "LP markdown:\n"
            f"# {title}\n\n"
            f"## Hero\n{theme} の成果につながるLP\n\n"
            "## Main copy\n"
            f"{theme} の魅力を短く強く伝え、相談導線へつなげる。\n\n"
            "## CTA\n無料相談はこちら\n"
        )

    if task_type == "ec_improvement":
        return (
            "before/after改善案:\n"
            f"- 対象: {theme}\n"
            "- before: 情報が散在し、訴求が弱い\n"
            "- after: ベネフィット先頭、比較表、FAQ、CTAを整理\n"
            "- コピー改善: 一文目で価値訴求\n"
            "- 画像案: 使用シーン、比較、実績、導線\n"
            "- SEO案: 商品名 + 用途 + 比較 + 導入事例\n"
            "- 優先度: 高\n"
        )

    if task_type == "sns_script":
        return (
            "ショート動画台本:\n"
            f"- テーマ: {theme}\n"
            "- フック: 3秒で違いが伝わる冒頭\n"
            "- 台本: 問題提起 → 解決策 → 行動喚起\n"
            "- カット構成: 0-3秒 / 3-8秒 / 8-15秒\n"
        )

    if task_type == "sales_outreach":
        return (
            "営業テンプレ:\n"
            f"- テーマ: {theme}\n"
            "- ターゲット業種: 中小企業\n"
            "- ターゲットリスト: 10件想定\n"
            "- DMテンプレ: 課題仮説 + 改善提案 + 相談導線\n"
            "- メールテンプレ: 現状課題 + 支援内容 + 事例 + CTA\n"
            "[HUMAN REQUIRED]\n"
            "内容: 実送信先・契約条件・送信文最終確認\n"
            "理由: 外部接続と契約判断は人間確認が必要\n"
            "優先度: 高\n"
            "推奨: 送信前に10件の対象先を人間確認\n"
        )

    return ""

def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT id,title,description,spec,branch_name,pr_number,pr_url,dev_stage,dev_attempts,source_ai,target_system,improvement_type
        FROM dev_proposals
        WHERE status='approved' AND coalesce(quality_score,0) >= 60
          AND coalesce(spec,'')!=''
          AND (dev_stage IS NULL OR dev_stage='' OR dev_stage='approved')
        ORDER BY CASE WHEN coalesce(source_ai,'')='business_activation' THEN 0 ELSE 1 END, id ASC
        LIMIT 1
    """).fetchone()

    if not row:
        print("no approved proposals", flush=True)
        return 0

    pid = int(row["id"])
    kai(conn, pid, "picked", branch_name=(row["branch_name"] or ""), title=(row["title"] or ""))

    title = (row["title"] or f"proposal {pid}").strip()
    branch = row["branch_name"] or f"dev/proposal-{pid}"
    description = row["description"] or ""
    spec = row["spec"] or ""
    source_ai = (row["source_ai"] or "").strip()
    target_system = (row["target_system"] or "").strip()
    improvement_type = (row["improvement_type"] or "").strip()
    business_output = render_business_output(title, spec) if source_ai == "business_activation" else ""

    sh(["/usr/bin/git", "checkout", BASE_BRANCH])
    kai(conn, pid, "git_base", base=BASE_BRANCH)
    sh(["/usr/bin/git", "fetch", "origin", BASE_BRANCH])
    sh(["/usr/bin/git", "reset", "--hard", "origin/" + BASE_BRANCH])
    sh(["/usr/bin/git", "clean", "-fd"])

    exists = sh(["/usr/bin/git", "ls-remote", "--heads", "origin", branch], capture=True)
    if exists:
        sh(["/usr/bin/git", "checkout", branch])
        sh(["/usr/bin/git", "fetch", "origin", branch])
        sh(["/usr/bin/git", "reset", "--hard", "origin/" + branch])
        sh(["/usr/bin/git", "clean", "-fd"])
    else:
        sh(["/usr/bin/git", "checkout", "-B", branch])

    os.makedirs(os.path.join(REPO, "dev_autogen"), exist_ok=True)
    fpath = os.path.join(REPO, "dev_autogen", f"p{pid}.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"id={pid}\n")
        f.write(f"title={title}\n")
        f.write(f"ts={now()}\n")
        f.write(f"source_ai={source_ai}\n")
        f.write(f"target_system={target_system}\n")
        f.write(f"improvement_type={improvement_type}\n\n")
        if business_output:
            f.write(business_output[:4000])
        else:
            f.write(description[:4000])

    sh(["/usr/bin/git", "add", fpath])
    sh(["/usr/bin/git", "commit", "-m", f"dev: proposal #{pid} bootstrap PR"])
    sh(["/usr/bin/git", "push", "-u", "origin", branch])
    kai(conn, pid, "git_push", branch=branch)

    prj = sh(
        [
            "/opt/homebrew/bin/gh",
            "pr",
            "create",
            "--base",
            BASE_BRANCH,
            "--head",
            branch,
            "--title",
            f"[dev] {title} (#{pid})",
            "--body",
            f"proposal_id: {pid}\nbranch: {branch}\n\n{description}",
        ],
        capture=True,
    )
    pr_url = prj.strip().splitlines()[-1].strip()
    pr_num = None
    m = re.search(r"/pull/(\d+)", pr_url)
    if m:
        pr_num = int(m.group(1))

    conn.execute(
        """
        UPDATE dev_proposals
        SET status='pr_created', dev_stage='pr_created',
            pr_number=COALESCE(?,pr_number),
            pr_url=COALESCE(?,pr_url),
            dev_attempts=COALESCE(dev_attempts,0)+1
        WHERE id=?
        """,
        (pr_num, pr_url, pid),
    )

    conn.execute(
        """
        insert into ceo_hub_events(event_type,title,body,proposal_id,pr_url)
        values(?,?,?,?,?)
        """,
        (
            "pr_created",
            f"PR作 成 : {title}",
            f"proposal_id={pid} / PR={pr_url}",
            pid,
            pr_url,
        ),
    )

    if source_ai == "business_activation":
        conn.execute(
            """
            insert or replace into learning_results
            (proposal_id,title,source_ai,target_system,improvement_type,impact_score,impact_level,impact_reason,result_score,result_type,result_note,success_flag,learning_summary,merged_at,created_at)
            values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            """,
            (
                pid,
                title,
                source_ai,
                target_system,
                improvement_type,
                0.8,
                "medium",
                "business executor output generated",
                0.8,
                "business_task_ready",
                business_output[:2000],
                1,
                f"business task executed: {improvement_type}",
                now(),
            ),
        )

    kai(conn, pid, "db_updated", pr_url=pr_url, pr_number=pr_num)
    conn.commit()

    print(
        json.dumps(
            {
                "proposal_id": pid,
                "branch": branch,
                "pr_number": pr_num,
                "pr_url": pr_url,
            },
            ensure_ascii=False,
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
