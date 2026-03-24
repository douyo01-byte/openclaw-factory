import os
import re
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH", "data/openclaw.db")

def parse_kv_block(text: str):
    out = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out

def detect_business_task(body: str):
    meta = parse_kv_block(body)
    task_type = (meta.get("task_type") or "").strip()
    roles = [x.strip() for x in (meta.get("roles") or "").split(",") if x.strip()]
    return task_type, roles, meta

def build_business_spec(task_type: str, roles: list[str], meta: dict):
    theme = meta.get("theme", "")
    deliverables = meta.get("deliverables", "")
    constraints = meta.get("constraints", "")
    role_text = ",".join(roles)

    if task_type == "lp_generation":
        return f"""[BUSINESS_TASK]
task_type=lp_generation
roles={role_text}
theme={theme}
deliverables={deliverables}
constraints={constraints}

output_format:
- LP markdown
- main copy
- CTA
"""

    if task_type == "ec_improvement":
        return f"""[BUSINESS_TASK]
task_type=ec_improvement
roles={role_text}
theme={theme}
deliverables={deliverables}
constraints={constraints}

output_format:
- before/after 改善案
- コピー改善
- 画像案
- SEO案
- 優先度
"""

    if task_type == "sns_script":
        return f"""[BUSINESS_TASK]
task_type=sns_script
roles={role_text}
theme={theme}
deliverables={deliverables}
constraints={constraints}

output_format:
- フック
- 5〜15秒台本
- カット構成
"""

    if task_type == "sales_outreach":
        return f"""[BUSINESS_TASK]
task_type=sales_outreach
roles={role_text}
theme={theme}
deliverables={deliverables}
constraints={constraints}

output_format:
- ターゲット業種
- ターゲットリスト10件
- DMテンプレ
- メールテンプレ
- [HUMAN REQUIRED]
内容:
理由:
優先度:
推奨:
"""

    return ""

def run():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "select id,from_username,from_name,text from inbox_commands where status='new' order by id asc limit 200"
    ).fetchall()

    for r in rows:
        txt = (r["text"] or "").strip()
        txt = re.sub(r"^\s*開\s*発\s*提\s*案\s*:\s*", "提案:", txt)
        txt_nospace = re.sub(r"\s+", "", txt)
        who = r["from_username"] or r["from_name"] or ""

        m = re.match(r"^提案:\s*(.+)$", txt, re.S)
        if m:
            body = m.group(1).strip()
            title = (body.splitlines()[0].strip() if body else "proposal")[:80]
            base = re.sub(r"[^a-z0-9]+", "-", (who or "user").lower()).strip("-")[:24] or "user"
            branch = f"dev/{base}-proposal-{r['id']}"

            task_type, roles, meta = detect_business_task(body)
            spec = build_business_spec(task_type, roles, meta)

            category = "automation"
            target_system = "executor"
            improvement_type = "stabilize"
            quality_score = 60
            source_ai = "command_executor"

            if task_type:
                category = "business"
                target_system = task_type.split("_")[0]
                improvement_type = task_type
                quality_score = 80
                source_ai = "business_activation"

            conn.execute(
                """insert into dev_proposals
                (title,description,spec,branch_name,status,created_at,category,target_system,improvement_type,quality_score,source_ai,dev_stage,spec_stage)
                values(?,?,?,?,?,datetime('now'),?,?,?,?,?,?,?)""",
                (
                    title,
                    body,
                    spec,
                    branch,
                    "approved" if task_type else "proposed",
                    category,
                    target_system,
                    improvement_type,
                    quality_score,
                    source_ai,
                    "approved" if task_type else "",
                    "refined" if task_type else "",
                ),
            )
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^(ok|hold)\s+(\d+)\s*$", txt, re.I)
        if m:
            cmd = m.group(1).lower()
            pid = int(m.group(2))
            st = "approved" if cmd == "ok" else "hold"
            conn.execute("update dev_proposals set status=? where id=?", (st, pid))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^req\s+(\d+)\s+(.+)$", txt, re.I | re.S)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='req' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^承認します#?(\d+)$", txt_nospace)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='approved' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^承認#?(\d+)$", txt_nospace)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='approved' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^保留#?(\d+)$", txt_nospace)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='hold' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        m = re.match(r"^質問#?(\d+)(.+)$", txt_nospace, re.S)
        if m:
            pid = int(m.group(1))
            conn.execute("update dev_proposals set status='needs_info' where id=?", (pid,))
            conn.execute(
                "update inbox_commands set status='applied', applied_at=datetime('now'), error=null where id=?",
                (r["id"],),
            )
            continue

        conn.execute(
            "update inbox_commands set status='ignored', applied_at=datetime('now'), error=? where id=?",
            ("unrecognized", r["id"]),
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run()
