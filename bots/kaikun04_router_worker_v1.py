
def force_exec(text):
    text = (text or "").strip()
    if "[EXEC]" in text:
        return text
    return "[EXEC]\nscript=run_python.sh\narg=mode=auto_task;task=" + text[:80]

import os
import re
import sqlite3
import time
from contextlib import contextmanager
from difflib import SequenceMatcher

import requests

from bots.autoagent_text_utils_v1 import clean_text
from bots.self_improvement_proposal_feedback_v1 import build_exec_feedback_block
from bots.self_improvement_proposal_feedback_v1 import load_proposal_pattern_hints


def force_exec(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "[EXEC]\nscript=log_check.sh"
    if text.startswith("[EXEC]") and "script=" in text:
        return text
    compact = " ".join(text.split())[:120]
    return "[EXEC]\nscript=run_python.sh\narg=mode=auto_task;task=" + compact


def decide_mode(text: str) -> str:
    t0 = (text or "").strip()
    if "[FORCE_CHAT]" in t0:
        return "CHAT"
    if t0.startswith("[GOAL_PLAN]"):
        return "THINK"
    if "[GOAL_IMPL]" in t0:
        return "THINK"
    t = t0.lower()
    if "[exec]" in t or "実 行 " in t or "run" in t:
        return "EXEC"
    if "作 っ て " in t or "生 成 " in t or "lp" in t:
        return "DOC"
    if "分 析 " in t or "教 え て " in t:
        return "THINK"
    return "CHAT"
    if t0.startswith("[GOAL_PLAN]"):
        return "THINK"
    t = text.lower()
    if "[exec]" in t or "実行" in t or "run" in t:
        return "EXEC"
    if "作って" in t or "生成" in t or "lp" in t:
        return "DOC"
    if "分析" in t or "教えて" in t:
        return "THINK"
    return "CHAT"

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("KAIKUN04_ROUTER_WORKER_SLEEP", "5"))
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
MODEL = (os.environ.get("KAIKUN04_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-5-mini").strip()

TASK_ID_RE = re.compile(r"\[TASK_ID:\d+\]")
TAG_RE = re.compile(r"^\[(THINK|TASK|MODE:[^\]]+)\]\s*$", re.MULTILINE)
SPACE_RE = re.compile(r"[ \t\u3000]+")
MULTI_NL_RE = re.compile(r"\n{3,}")

EXEC_BLOCK_RE = re.compile(r"(?ms)\[EXEC\]\s*\n\s*script=([A-Za-z0-9_.-]+)")
EXEC_LINE_RE = re.compile(r"(?m)^(script|arg)=([^\n]*)$")
ALLOWED_EXEC_SCRIPTS = {
    "db_health.sh",
    "git_status.sh",
    "status_core.sh",
    "kick_service.sh",
    "route_smoke.sh",
    "gh_pr_create.sh",
    "gh_pr_merge.sh",
    "git_commit_push.sh",
    "restart_service.sh",
    "fix_db.sh",
    "deploy_safe.sh",
    "run_python.sh",
}
AUTO_EXEC_MIN_WEIGHT = float(os.environ.get("KAIKUN04_AUTO_EXEC_MIN_WEIGHT", "0.8"))
AUTO_EXEC_MIN_SUCCESS = int(os.environ.get("KAIKUN04_AUTO_EXEC_MIN_SUCCESS", "1"))
AUTO_EXEC_PROMPT_RE = re.compile(r"(core\s*health|health\s*check|healthを|ヘルス|健[\s\u3000]*康|db[\s\u3000]*health)", re.I)

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

追加ルール:
- EXEC を出すのは本当に有用なときだけ
- EXEC を出す場合は返信の最後に1つだけ
- EXEC 形式は必ず次の2行だけ
[EXEC]
script=<allowlisted_script_name>
- bash / sh / zsh / python / command列 / 引数直書きは禁止
- 許可 script:
  - db_health.sh
  - git_status.sh
  - status_core.sh
  - kick_service.sh
  - route_smoke.sh
  - gh_pr_create.sh
  - gh_pr_merge.sh
  - git_commit_push.sh
- 実行が不要なときは EXEC を出さない
- CTO / CMO / COO / 開発 / 市場 / 訴求 / 運用 / 本命事業 / タスク登録 を求められた場合は、
  reply本文中に実行可能なタスク行を3件以上含めること
- タスク行の形式は次を使うこと
[TASK][CTO] ...
[TASK][CMO] ...
[TASK][COO] ...
"""

def has_exec_block(text: str) -> bool:
    return bool(EXEC_BLOCK_RE.search((text or "").strip()))

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
    lines = [f"script={script}"]
    block = m.group(0) if m else ""
    for key, value in EXEC_LINE_RE.findall(block):
        if key == "arg":
            lines.append(f"arg={value.strip()}")
            break
    clean = "[EXEC]\n" + "\n".join(lines)
    return re.sub(r"(?ms)\n*\[EXEC\][\s\S]*$", "\n\n" + clean, s).strip()

@contextmanager
def conn():
    last = None
    c = None
    for _ in range(5):
        try:
            c = sqlite3.connect(DB, timeout=30)
            c.row_factory = sqlite3.Row
            c.execute("pragma busy_timeout=30000")
            try:
                c.execute("pragma journal_mode=WAL")
            except Exception:
                pass
            break
        except sqlite3.OperationalError as e:
            last = e
            time.sleep(1)
    if c is None:
        raise last
    try:
        yield c
    except Exception:
        c.rollback()
        raise
    else:
        c.commit()
    finally:
        c.close()

def infer_exec_context(text: str, script: str) -> str:
    raw = ((text or "") + "\n" + (script or "")).lower()
    t = raw
    for ch in [" ", "　", "\n", "\r", "\t"]:
        t = t.replace(ch, "")

    if any(k in t for k in ["telegram経路", "telegramの経路", "telegram", "tg_", "chat_id", "finisher", "pollloop"]):
        return "telegram"
    if any(k in t for k in ["サービスの状態", "サービス", "service", "launchctl", "restart", "起動", "再起動"]):
        return "service"
    if any(k in t for k in ["api_server", "apiserver", "api", "endpoint", "webhook"]):
        return "api"
    if any(k in t for k in ["routing", "routingの状態", "ルーティング"]):
        return "routing"
    if any(k in t for k in ["deploy", "deployの状態", "デプロイ"]):
        return "deploy"
    if any(k in t for k in ["db", "database", "sqlite", "データベース", "db_health"]):
        return "db"
    if any(k in t for k in ["health", "ヘルス", "健全", "稼働", "status_core", "coreservice", "コア"]):
        return "health"
    if any(k in t for k in ["route", "router", "routing", "経路", "導線"]):
        return "routing"
    if any(k in t for k in ["lp", "landingpage", "preview", "cta", "hero", "訴求"]):
        return "lp"
    if any(k in t for k in ["git", "pr", "merge", "commit", "branch"]):
        return "git"
    return "general"

def choose_top_exec_scripts(prompt: str = "", text: str = "", limit: int = 3) -> list[str]:
    context = infer_exec_context((prompt or "") + "\n" + (text or ""), "")
    keys = []
    try:
        with conn() as c:
            rows = c.execute("""
                select pattern_key
                from learning_patterns
                where pattern_type='self_improvement_exec'
                  and coalesce(weight,0) >= ?
                  and coalesce(success_count,0) >= ?
                  and pattern_key like ?
                order by weight desc, success_count desc, sample_count desc, id desc
                limit ?
            """, (AUTO_EXEC_MIN_WEIGHT, AUTO_EXEC_MIN_SUCCESS, f"context={context}|script=%", limit)).fetchall()
            if not rows:
                rows = c.execute("""
                    select pattern_key
                    from learning_patterns
                    where pattern_type='self_improvement_exec'
                      and coalesce(weight,0) >= ?
                      and coalesce(success_count,0) >= ?
                      and pattern_key like 'script=%'
                    order by weight desc, success_count desc, sample_count desc, id desc
                    limit ?
                """, (AUTO_EXEC_MIN_WEIGHT, AUTO_EXEC_MIN_SUCCESS, limit)).fetchall()
            keys = [((r["pattern_key"] or "").strip()) for r in rows]
    except Exception:
        keys = []
    out = []
    for key in keys:
        if key.startswith("context=") and "|script=" in key:
            script = key.split("|script=", 1)[1].strip()
        elif key.startswith("script="):
            script = key.split("=", 1)[1].strip()
        else:
            continue
        if script in ALLOWED_EXEC_SCRIPTS and script not in out:
            out.append(script)
    return out

def choose_auto_exec_script(prompt: str = "", text: str = "") -> str:
    prompt_context = infer_exec_context(prompt or "", "")
    text_context = infer_exec_context(text or "", "")
    context = prompt_context if prompt_context != "general" else text_context
    forced_map = {
        "db": "db_health.sh",
        "deploy": "deploy_safe.sh",
    }
    if context in forced_map:
        return forced_map[context]
    xs = choose_top_exec_scripts(prompt, text, 3)
    return xs[0] if xs else ""

def maybe_append_auto_exec(prompt: str, text: str) -> str:
    s = (text or "").strip()
    if not s:
        return s
    combined = ((prompt or "") + "\n" + s).strip()
    if "[AUTO_GOAL]" in combined or "[AUTO_GOAL_TRIGGER]" in combined:
        return normalize_exec_block(s)
    if has_exec_block(s):
        forced = choose_auto_exec_script(prompt, s)
        base = EXEC_BLOCK_RE.sub("", s).strip()
        if forced:
            return normalize_exec_block(f"{base}\n\n[EXEC]\nscript={forced}")
        return normalize_exec_block(base)
    if not AUTO_EXEC_PROMPT_RE.search(combined):
        return s
    script = choose_auto_exec_script(prompt, s)
    if not script:
        return s
    base = EXEC_BLOCK_RE.sub("", s).strip()
    return normalize_exec_block(f"{base}\n\n[EXEC]\nscript={script}")

def load_exec_pattern_hints(prompt: str = "", text: str = "") -> str:
    context = infer_exec_context((prompt or "") + "\n" + (text or ""), "")
    scripts = choose_top_exec_scripts(prompt, text, 3)
    hints = [f"- context={context}|script={x}" for x in scripts]
    if not hints:
        return ""
    return "\n".join([
        f"実行提案ヒント: context={context}",
        "過去に成功した allowlisted EXEC 候補があります。",
        *hints,
        "必要性が低いときは EXEC を出さないこと。",
        "出す場合は末尾に 1つだけ出すこと。"
    ])

def force_clean_exec(text: str) -> str:
    if not text:
        return text
    if "[EXEC]" in text and "script=" not in text:
        return re.sub(r"(?ms)\[EXEC\][\s\S]*$", "", text).strip()
    return text

def extract_exec_script(reply_text: str) -> str:
    m = EXEC_BLOCK_RE.search((reply_text or "").strip())
    if not m:
        return ""
    script = (m.group(1) or "").strip()
    if script not in ALLOWED_EXEC_SCRIPTS:
        return ""
    return script

def build_exec_child_payload(reply_text: str, script: str) -> str:
    lines = [f"script={script}"]
    m = re.search(r"(?ms)\[EXEC\](.*)$", reply_text or "")
    block = m.group(1) if m else ""
    for key, value in EXEC_LINE_RE.findall(block):
        if key == "arg":
            lines.append(f"arg={value.strip()}")
    return "[EXEC]\n" + "\n".join(lines)

def insert_exec_child(c, source_command_id: int, parent_task_id: int, script: str, reply_text: str = "") -> int:
    task_text = build_exec_child_payload(reply_text, script)
    c.execute("""
        insert into router_tasks(
          source_command_id, parent_task_id, mode, target_bot, task_text, status, created_at, updated_at
        ) values(
          ?, ?, 'EXEC', 'ops_exec', ?, 'new', datetime('now'), datetime('now')
        )
    """, (source_command_id, parent_task_id, task_text))
    return int(c.execute("select last_insert_rowid()").fetchone()[0])

def mark_exec_direct(c, parent_task_id: int, child_task_id: int):
    c.execute("""
        update router_tasks
        set exec_bridge_status='direct',
            exec_child_task_id=?,
            updated_at=datetime('now')
        where id=?
    """, (child_task_id, parent_task_id))

def log_exec_direct(c, parent_task_id: int, child_task_id: int, source_command_id: int, script: str, reply_text: str):
    source_text = ""
    try:
        row = c.execute("select coalesce(text,'') as text from inbox_commands where id=?", (source_command_id,)).fetchone()
        source_text = (row["text"] if row else "") or ""
    except Exception:
        source_text = ""
    context = infer_exec_context(source_text, script)
    reusable = f"context={context}|script={script}"
    c.execute("""
        insert into self_improvement_log(
          parent_task_id, child_task_id, source_command_id, kind,
          problem, fix, result, reusable_pattern,
          status, parent_reply_head, child_result_head,
          created_at, applied_at, updated_at
        ) values(
          ?, ?, ?, 'exec_direct',
          'direct exec from kaikun',
          ?, 'queued_child_task', ?,
          'queued', ?, '',
          datetime('now'), '', datetime('now')
        )
    """, (
        parent_task_id,
        child_task_id,
        source_command_id,
        f"script={script}",
        reusable,
        (reply_text or "")[:300]
    ))

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)").fetchall()}
    required = {
        "clean_prompt",
        "validation_status",
        "validation_reason",
        "retry_count",
        "parent_task_id",
        "task_role",
        "reply_text",
        "finished_at",
        "started_at",
        "exec_bridge_status",
        "exec_child_task_id",
    }
    missing = sorted(required - cols)
    if missing:
        raise RuntimeError(
            f"schema_missing table=router_tasks cols={','.join(missing)} "
            "apply migrations/20260513_router_core_schema_v1.sql first"
        )
    inbox_cols = {r["name"] for r in c.execute("pragma table_info(inbox_commands)").fetchall()}
    inbox_required = {"router_finish_status", "router_task_id", "updated_at"}
    inbox_missing = sorted(inbox_required - inbox_cols)
    if inbox_missing:
        raise RuntimeError(
            f"schema_missing table=inbox_commands cols={','.join(inbox_missing)} "
            "apply migrations/20260513_router_core_schema_v1.sql first"
        )
    sil_cols = {r["name"] for r in c.execute("pragma table_info(self_improvement_log)").fetchall()}
    sil_required = {
        "parent_task_id", "child_task_id", "source_command_id", "kind",
        "problem", "fix", "result", "reusable_pattern", "status",
        "parent_reply_head", "child_result_head", "applied_at", "updated_at",
    }
    sil_missing = sorted(sil_required - sil_cols)
    if sil_missing:
        raise RuntimeError(
            f"schema_missing table=self_improvement_log cols={','.join(sil_missing)} "
            "apply migrations/20260513_router_core_schema_v1.sql first"
        )

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
    if "[PLANNER]" in (prompt or "") or "[GOAL_IMPL]" in (prompt or ""):
        t = (output or "").strip().lower()
        if "[exec]" in t and "script=" in t:
            return True, ""

    p = (prompt or "").strip()
    o = (output or "").strip()
    if not o:
        return False, "empty"

    low_p = p.lower()
    low_o = o.lower()

    if "rewrite" in low_p or "rewritten_text" in low_p:
        if len(o) < 40:
            return False, "too_short"
        return True, "ok"

    if len(o) < 80:
        return False, "too_short"
    if similarity(p, o) > 0.92:
        return False, "too_similar"
    if "[mode:chat]" not in low_p and "html" in low_p and "<html" not in low_o and "```html" not in low_o:
        return False, "missing_html"
    if "3案" in p and not any(x in o for x in ["1.", "1案", "A案", "①", "[TASK][CTO]", "[TASK][CMO]", "[TASK][COO]"]):
        return False, "missing_3_variants"
    if "cta" in low_p and "cta" not in low_o:
        return False, "missing_cta"
    return True, "ok"

def call_llm(task_id: int, prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")
    exec_hints = load_exec_pattern_hints(prompt, prompt)
    feedback_hints = build_exec_feedback_block()
    extra = "\n\n".join([x for x in [feedback_hints, exec_hints] if x])
    prompt2 = prompt if not extra else f"{prompt}\n\n{extra}"
    user_prompt = f"[TASK_ID:{task_id}]\n\n{prompt2}"
    retry_delays = (5, 15, 30)
    for attempt in range(1, len(retry_delays) + 2):
        try:
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
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt > len(retry_delays):
                raise
            print(
                f"[kaikun04_router_worker_v1] openai_transport_retry "
                f"task_id={task_id} attempt={attempt} err={type(e).__name__}",
                flush=True,
            )
            time.sleep(retry_delays[attempt - 1])
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
        select
          id,
          source_command_id,
          coalesce(task_role,'') as task_role,
          coalesce(mode,'') as mode,
          task_text,
          coalesce(retry_count,0) as retry_count,
          coalesce(status,'new') as status
        from router_tasks
        where coalesce(target_bot,'')='kaikun04'
          and (
            coalesce(status,'new') in ('new','invalid_output')
            or (
              coalesce(status,'new')='started'
              and datetime(coalesce(updated_at, started_at, created_at, '1970-01-01')) <= datetime('now', '-30 minutes')
            )
          )
        order by
          case
            when coalesce(task_text,'') like '[GOAL_PLAN]%' then 0
            when coalesce(task_text,'') like '%[GOAL_IMPL]%' then 1
            when coalesce(task_role,'')='PLANNER' then 2
            when coalesce(task_role,'')='AUTO_DEV' then 3
            when task_text like '[AUTO_GOAL%' then 3
            else 4
          end,
          datetime(coalesce(updated_at, created_at, '1970-01-01')) desc,
          id desc
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
    reply = (reply or "").strip()
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
    if cmd_id:
        c.execute("""
            update inbox_commands
            set router_finish_status='applied',
                router_task_id=?,
                updated_at=datetime('now')
            where id=?
        """, (task_id, cmd_id))

TASK_LINE_RE = re.compile(r"^\[TASK\]\[(CTO|CMO|COO)\]\s*(.+)$", re.I)

def infer_target_bot_from_role(role: str) -> str:
    return "kaikun04"

def extract_business_tasks(reply_text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for raw in (reply_text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = TASK_LINE_RE.match(line)
        if not m:
            continue
        role = (m.group(1) or "").upper().strip()
        body = (m.group(2) or "").strip()
        if len(body) < 8:
            continue
        out.append((role, body))
    if out:
        return out[:6]

    fallback: list[tuple[str, str]] = []
    for raw in (reply_text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "CTO" in line or "開発" in line:
            fallback.append(("CTO", re.sub(r"^[-*0-9. ①②③]+", "", line).strip()))
        elif "CMO" in line or "市場" in line or "訴求" in line or "マーケ" in line:
            fallback.append(("CMO", re.sub(r"^[-*0-9. ①②③]+", "", line).strip()))
        elif "COO" in line or "運用" in line or "進捗" in line:
            fallback.append(("COO", re.sub(r"^[-*0-9. ①②③]+", "", line).strip()))
    uniq: list[tuple[str, str]] = []
    seen = set()
    for role, body in fallback:
        key = (role, body)
        if body and key not in seen:
            uniq.append((role, body))
            seen.add(key)
    return uniq[:6]

def insert_business_tasks(c, parent_task_id: int, source_command_id: int, reply_text: str) -> list[int]:
    task_specs = extract_business_tasks(reply_text)
    child_ids: list[int] = []
    for role, body in task_specs:
        target_bot = infer_target_bot_from_role(role)
        task_text = f"[ROLE:{role}]\n{body}"
        c.execute("""
            insert into router_tasks(
              source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
            ) values(
              ?, ?, ?, 'THINK', ?, ?, 'new', datetime('now'), datetime('now')
            )
        """, (source_command_id, parent_task_id, role, target_bot, task_text))
        child_ids.append(int(c.execute("select last_insert_rowid()").fetchone()[0]))
    return child_ids

def insert_role_exec_tasks(c, source_command_id: int, parent_task_id: int, task_specs: list[tuple[str, str]]) -> list[int]:
    child_ids: list[int] = []
    for role, body in task_specs:
        role = (role or "").upper().strip()
        body = (body or "").strip()
        if not body:
            continue
        if role == "CTO":
            task_text = f"[EXEC]\nscript=run_python.sh\narg=mode=ctogen_exec;task={body}"
        elif role == "CMO":
            task_text = f"[EXEC]\nscript=run_python.sh\narg=mode=lpgen_exec;task={body}"
        elif role == "COO":
            task_text = f"[EXEC]\nscript=run_python.sh\narg=mode=runbook_gen_exec;task={body}"
        else:
            continue
        c.execute("""
            insert into router_tasks(
              source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
            ) values(
              ?, ?, ?, 'EXEC', 'ops_exec', ?, 'new', datetime('now'), datetime('now')
            )
        """, (source_command_id, parent_task_id, role, task_text))
        child_ids.append(int(c.execute("select last_insert_rowid()").fetchone()[0]))
    return child_ids


def tick():
    done = 0
    with conn() as c:
        ensure_schema(c)
        rows = fetch_rows(c)
        for r in rows:
            task_id = r["id"]
            source_command_id = int(r["source_command_id"] or 0)
            clean = clean_prompt(r["task_text"])
            if not clean:
                mark_retry(c, task_id, clean, "empty_clean_prompt")
                c.commit()
                continue
            print(f"[k04] picked task_id={task_id}", flush=True)
            mark_started(c, task_id)
            c.commit()
            try:
                cols = set(r.keys())
                db_mode = (r["mode"] or "").strip().upper() if "mode" in cols and r["mode"] is not None else ""
                mode = db_mode if db_mode else decide_mode(clean)
                prompt2 = f"[MODE:{mode}]\n{clean}"
                print(f"[k04] calling_llm task_id={task_id} db_mode={db_mode} mode={mode}", flush=True)
                reply = call_llm(task_id, prompt2)
                print(f"[k04] llm_done task_id={task_id}", flush=True)
                reply = clean_text(reply)
                reply = force_clean_exec(reply)
                reply = clean_text(reply)

                if (r["task_role"] or "").upper() == "PLANNER":
                    t = (reply or "").strip().lower()
                    if not ("[exec]" in t and "script=" in t):
                        compact = " ".join((reply or "").split())[:120]
                        if not compact:
                            compact = "LP改善 / 学習 / 自動化前進 の 次の1手を1つ決めて実行する"
                        reply = "[EXEC]\nscript=run_python.sh\narg=mode=auto_task;task=" + compact

                ok, reason = validate_output(prompt2, reply)
                if (r["task_role"] or "").upper() == "PLANNER":
                    t = (reply or "").strip().lower()
                    if "[exec]" in t and "script=" in t:
                        ok = True
                        reason = ""
                    else:
                        ok = False
                        reason = "planner_not_exec" ""
                if ok:
                    mark_done(c, task_id, source_command_id, clean, reply)
                    print(f"[k04] mark_done task_id={task_id}", flush=True)

                    script = extract_exec_script(reply)
                    auto_goal_task = "[AUTO_GOAL]" in clean or "[AUTO_GOAL_TRIGGER]" in clean
                    goal_plan_task = clean.strip().startswith("[GOAL_PLAN]")
                    goal_impl_task = "[GOAL_IMPL]" in clean
                    if script and not auto_goal_task and not goal_plan_task and not goal_impl_task:
                        try:
                            child_id = insert_exec_child(c, source_command_id, task_id, script, reply)
                            mark_exec_direct(c, task_id, child_id)
                            log_exec_direct(c, task_id, child_id, source_command_id, script, reply)
                            print(f"[kaikun04_router_worker_v1] exec_direct parent={task_id} child={child_id} script={script}", flush=True)
                        except Exception as e:
                            print(f"[kaikun04_router_worker_v1] exec_direct_err={e!r}", flush=True)
                    elif script and auto_goal_task:
                        print(f"[kaikun04_router_worker_v1] exec_direct_skip_auto_goal parent={task_id} script={script}", flush=True)
                    elif script and goal_plan_task:
                        print(f"[kaikun04_router_worker_v1] exec_direct_skip_goal_plan parent={task_id} script={script}", flush=True)
                    elif script and goal_impl_task:
                        try:
                            child_id = insert_exec_child(c, source_command_id, task_id, script, reply)
                            mark_exec_direct(c, task_id, child_id)
                            log_exec_direct(c, task_id, child_id, source_command_id, script, reply)
                            print(f"[kaikun04_router_worker_v1] exec_direct_goal_impl parent={task_id} child={child_id} script={script}", flush=True)
                        except Exception as e:
                            print(f"[kaikun04_router_worker_v1] exec_direct_goal_impl_err={e!r}", flush=True)
                    try:
                        goal_plan_task = clean.strip().startswith("[GOAL_PLAN]")
                        goal_impl_task = "[GOAL_IMPL]" in clean
                        if goal_plan_task or goal_impl_task:
                            task_specs = []
                            biz_child_ids = []
                            exec_child_ids = []
                        else:
                            task_specs = extract_business_tasks(reply)
                            biz_child_ids = insert_business_tasks(c, task_id, source_command_id, reply)
                            if biz_child_ids:
                                print(f"[kaikun04_router_worker_v1] business_tasks parent={task_id} children={biz_child_ids}", flush=True)
                            exec_child_ids = insert_role_exec_tasks(c, source_command_id, task_id, task_specs)
                            if exec_child_ids:
                                print(f"[kaikun04_router_worker_v1] role_exec_tasks parent={task_id} children={exec_child_ids}", flush=True)
                    except Exception as e:
                        print(f"[kaikun04_router_worker_v1] business_task_err={e!r}", flush=True)

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
