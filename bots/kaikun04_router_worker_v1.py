from __future__ import annotations
import json
import os
import re
import sqlite3
import time
from difflib import SequenceMatcher
import requests
from bots.self_improvement_proposal_feedback_v1 import build_exec_feedback_block
from bots.self_improvement_proposal_feedback_v1 import load_proposal_pattern_hints

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("KAIKUN04_ROUTER_WORKER_SLEEP", "5"))
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
MODEL = (os.environ.get("KAIKUN04_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-5-mini").strip()

TASK_ID_RE = re.compile(r"\[TASK_ID:\d+\]")
TAG_RE = re.compile(r"^\[(THINK|TASK|MODE:[^\]]+)\]\s*$", re.MULTILINE)
SPACE_RE = re.compile(r"[ \t\u3000]+")
MULTI_NL_RE = re.compile(r"\n{3,}")

EXEC_BLOCK_RE = re.compile(r"(?ms)^\[EXEC\]\s*script=([A-Za-z0-9_.-]+)\s*$")
ALLOWED_EXEC_SCRIPTS = {
    "db_health.sh",
    "git_status.sh",
    "status_core.sh",
    "kick_service.sh",
    "route_smoke.sh",
    "gh_pr_create.sh",
    "gh_pr_merge.sh",
    "git_commit_push.sh",
}
AUTO_EXEC_MIN_WEIGHT = float(os.environ.get("KAIKUN04_AUTO_EXEC_MIN_WEIGHT", "0.8"))
AUTO_EXEC_MIN_SUCCESS = int(os.environ.get("KAIKUN04_AUTO_EXEC_MIN_SUCCESS", "1"))
AUTO_EXEC_PROMPT_RE = re.compile(r"(core\s*health|health\s*check|healthを|ヘルス|健[\s\u3000]*康|db[\s\u3000]*health)", re.I)

def normalize_exec_block(text: str) -> str:
    s = (text or "").strip()
    m = EXEC_BLOCK_RE.search(s)
    if not m:
        s = re.sub(r"(?ms)\n*EXEC[^\n]*$", "", s).strip()
        s = re.sub(r"(?ms)\n*\[EXEC\][\s\S]*$", "", s).strip()
        return s
    script = (m.group(1) or "").strip()
    if script not in ALLOWED_EXEC_SCRIPTS:
        s = re.sub(r"(?ms)\n*\[EXEC\][\s\S]*$", "", s).strip()
        return s
    clean = f"[EXEC]\nscript={script}"
    return re.sub(r"(?ms)\n*\[EXEC\][\s\S]*$", "\n\n" + clean, s).strip()

SYSTEM_PROMPT = """あなたは OpenClaw の Kaikun04 です。
目的は、タスク本文に対して実務で使える完成回答を返すことです。
禁止:
- ユーザー入力のオウム返し
- 指示文の再掲だけで終わること
- メタ説明
- 不要な前置き
必須:
- 依頼の要求物をすべて埋める
- 具体的に返す
- HTMLを求められたら、そのままコピペできるHTMLを含める
- 3案を求められたら3案返す
- 返信冒頭は必ず [TASK_ID:番号]

追 加 ル ー ル :
- EXEC を 出 す の は 本 当 に 有 用 な と き だ け
- EXEC を 出 す 場 合 は 返 信 の 最 後 に 1つ だ け
- EXEC 形 式 は 必 ず 次 の 2行 だ け
[EXEC]
script=<allowlisted_script_name>
- bash / sh / zsh / python / command列 / 引 数 直 書 き は 禁 止
- 許 可 script:
  - db_health.sh
  - git_status.sh
  - status_core.sh
  - kick_service.sh
  - route_smoke.sh
  - gh_pr_create.sh
  - gh_pr_merge.sh
  - git_commit_push.sh
- 実 行 が 不 要 な と き は EXEC を 出 さ な い
"""

def has_exec_block(text: str) -> bool:
    return bool(EXEC_BLOCK_RE.search((text or "").strip()))

def choose_auto_exec_script() -> str:
    try:
        with conn() as c:
            row = c.execute("""
                select pattern_key
                from learning_patterns
                where pattern_type='self_improvement_exec'
                  and coalesce(weight,0) >= ?
                  and coalesce(success_count,0) >= ?
                order by weight desc, success_count desc, sample_count desc, id desc
                limit 1
            """, (AUTO_EXEC_MIN_WEIGHT, AUTO_EXEC_MIN_SUCCESS)).fetchone()
    except Exception:
        row = None
    key = ((row["pattern_key"] if row else "") or "").strip()
    if not key.startswith("script="):
        return ""
    script = key.split("=", 1)[1].strip()
    if script not in ALLOWED_EXEC_SCRIPTS:
        return ""
    return script

def maybe_append_auto_exec(prompt: str, text: str) -> str:
    s = (text or "").strip()
    if not s:
        return s
    if has_exec_block(s):
        return normalize_exec_block(s)
    base = ((prompt or "") + "\n" + s).strip()
    if not AUTO_EXEC_PROMPT_RE.search(base):
        return s
    script = choose_auto_exec_script()
    if not script:
        return s
    return normalize_exec_block(f"{s}\n\n[EXEC]\nscript={script}")

def load_exec_pattern_hints() -> str:
    try:
        with conn() as c:
            rows = c.execute("""
                select pattern_key, weight
                from learning_patterns
                where pattern_type='self_improvement_exec'
                order by weight desc, success_count desc, sample_count desc
                limit 5
            """).fetchall()
    except Exception:
        rows = []
    hints = []
    for r in rows:
        k = (r["pattern_key"] or "").strip()
        if not k.startswith("script="):
            continue
        hints.append(f"- {k} weight={float(r['weight'] or 0):.3f}")
    if not hints:
        return ""
    return "\n".join([
        "実行提案ヒント:",
        "過去に成功した allowlisted EXEC パターンがあります。",
        *hints,
        "必要性が低いときは EXEC を出さないこと。",
        "出す場合は末尾に 1つだけ出すこと。"
    ])

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)").fetchall()}
    adds = {
        "clean_prompt": "alter table router_tasks add column clean_prompt text default ''",
        "validation_status": "alter table router_tasks add column validation_status text default ''",
        "validation_reason": "alter table router_tasks add column validation_reason text default ''",
        "retry_count": "alter table router_tasks add column retry_count integer default 0",
    }
    for k, sql in adds.items():
        if k not in cols:
            c.execute(sql)

def normalize_line(line: str) -> str:
    return SPACE_RE.sub(" ", line.replace("\r", "")).strip()

def clean_prompt(task_text: str) -> str:
    s = (task_text or "").replace("\r", "\n")
    s = TASK_ID_RE.sub("", s)
    s = TAG_RE.sub("", s)
    lines = []
    for raw in s.splitlines():
        line = normalize_line(raw)
        if not line:
            continue
        if line.startswith("返信の先頭に"):
            continue
        if line.startswith("sent_to_kaikun04:"):
            continue
        if line.startswith("Last login:"):
            continue
        if line.startswith("doyopc@"):
            continue
        if line.startswith("sqlite3 "):
            continue
        lines.append(line)
    s = "\n".join(lines).strip()
    return MULTI_NL_RE.sub("\n\n", s)

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a[:4000], b[:4000]).ratio()

def validate_output(prompt: str, output: str):
    p = (prompt or "").strip()
    o = (output or "").strip()
    if not o:
        return False, "empty"
    if len(o) < 180:
        return False, "too_short"
    if similarity(p, o) > 0.88:
        return False, "too_similar"
    low_p = p.lower()
    low_o = o.lower()
    if "html" in low_p and "<html" not in low_o and "```html" not in low_o:
        return False, "missing_html"
    if "3案" in p and not any(x in o for x in ["1.", "1案", "A案", "①"]):
        return False, "missing_3_variants"
    if "cta" in low_p and "cta" not in low_o:
        return False, "missing_cta"
    return True, "ok"

def call_llm(task_id: int, prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")
    exec_hints = load_exec_pattern_hints()
    feedback_hints = build_exec_feedback_block()
    extra = "\n\n".join([x for x in [feedback_hints, exec_hints] if x])
    prompt2 = prompt if not extra else f"{prompt}\n\n{extra}"
    user_prompt = f"[TASK_ID:{task_id}]\n\n{prompt2}"
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=180,
    )
    try:
        r.raise_for_status()
    except Exception:
        print(f"[kaikun04_router_worker_v1] openai_status={r.status_code}", flush=True)
        print(r.text[:4000], flush=True)
        raise
    j = r.json()
    text = (((j.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    text = normalize_exec_block(text)
    text = maybe_append_auto_exec(prompt, text)
    if not text.startswith(f"[TASK_ID:{task_id}]"):
        text = f"[TASK_ID:{task_id}]\n{text}"
    return text.strip()
def fetch_rows(c):


    return c.execute("""
        select id, source_command_id, task_text, coalesce(retry_count,0) as retry_count, coalesce(status,'new') as status
        from router_tasks
        where coalesce(target_bot,'')='kaikun04'
          and coalesce(reply_text,'')=''
          and coalesce(status,'new') in ('new','started','invalid_output')
        order by id asc
        limit 3
    """).fetchall()

def mark_started(c, task_id: int):
    c.execute("""
        update router_tasks
        set status='started',
            started_at=case when coalesce(started_at,'')='' then datetime('now') else started_at end,
            updated_at=datetime('now')
        where id=?
    """, (task_id,))

def mark_retry(c, task_id: int, clean: str, reason: str):
    c.execute("""
        update router_tasks
        set clean_prompt=?,
            validation_status='invalid_output',
            validation_reason=?,
            retry_count=coalesce(retry_count,0)+1,
            status=case when coalesce(retry_count,0)+1 >= 3 then 'failed' else 'invalid_output' end,
            updated_at=datetime('now')
        where id=?
    """, (clean, reason, task_id))

def mark_done(c, task_id: int, cmd_id: int, clean: str, reply: str):
    c.execute("""
        update router_tasks
        set clean_prompt=?,
            reply_text=?,
            validation_status='ok',
            validation_reason='',
            status='done',
            finished_at=datetime('now'),
            updated_at=datetime('now')
        where id=?
    """, (clean, reply, task_id))
    c.execute("""
        update inbox_commands
        set router_finish_status='applied',
            router_task_id=?,
            updated_at=datetime('now')
        where id=?
    """, (task_id, cmd_id))

def tick():
    done = 0
    with conn() as c:
        ensure_schema(c)
        rows = fetch_rows(c)
        for r in rows:
            task_id = r["id"]
            clean = clean_prompt(r["task_text"])
            if not clean:
                mark_retry(c, task_id, clean, "empty_clean_prompt")
                c.commit()
                continue
            mark_started(c, task_id)
            c.commit()
            try:
                reply = call_llm(task_id, clean)
                ok, reason = validate_output(clean, reply)
                if ok:
                    mark_done(c, task_id, r["source_command_id"], clean, reply)
                    c.commit()
                    done += 1
                    print(f"[kaikun04_router_worker_v1] done task_id={task_id}", flush=True)
                else:
                    mark_retry(c, task_id, clean, reason)
                    c.commit()
                    print(f"[kaikun04_router_worker_v1] retry task_id={task_id} reason={reason}", flush=True)
            except Exception as e:
                mark_retry(c, task_id, clean, f"llm_error:{type(e).__name__}")
                c.commit()
                print(f"[kaikun04_router_worker_v1] err task_id={task_id} err={e!r}", flush=True)
    print(f"[kaikun04_router_worker_v1] done={done}", flush=True)

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[kaikun04_router_worker_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
