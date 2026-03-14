from __future__ import annotations
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = Path("data/ai_meeting_digest_v1.state")

WINDOW_MIN = int(os.environ.get("AI_MEETING_DIGEST_WINDOW_MIN", "20"))
MIN_MERGED = int(os.environ.get("AI_MEETING_DIGEST_MIN_MERGED", "2"))
MIN_PR = int(os.environ.get("AI_MEETING_DIGEST_MIN_PR", "2"))
MIN_LEARN = int(os.environ.get("AI_MEETING_DIGEST_MIN_LEARN", "2"))
COOLDOWN_MIN = int(os.environ.get("AI_MEETING_DIGEST_COOLDOWN_MIN", "15"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    return con

def load_last_id() -> int:
    try:
        return int(STATE_PATH.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        return 0

def save_last_id(v: int):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(str(v), encoding="utf-8")

def recent_ai_meeting_exists(con: sqlite3.Connection) -> bool:
    row = con.execute("""
        select 1
        from ceo_hub_events
        where coalesce(event_type,'')='ai_meeting'
          and created_at >= datetime('now', ?)
        order by id desc
        limit 1
    """, (f"-{COOLDOWN_MIN} minutes",)).fetchone()
    return bool(row)

def counts_since(con: sqlite3.Connection, last_id: int):
    row = con.execute("""
        select
          coalesce(max(id),0) as max_id,
          sum(case when coalesce(event_type,'')='merged' then 1 else 0 end) as merged_cnt,
          sum(case when coalesce(event_type,'')='pr_created' then 1 else 0 end) as pr_cnt,
          sum(case when coalesce(event_type,'')='learning_result' then 1 else 0 end) as learn_cnt,
          sum(case when coalesce(event_type,'')='ai_employee' then 1 else 0 end) as emp_cnt
        from ceo_hub_events
        where id > ?
          and created_at >= datetime('now', ?)
    """, (last_id, f"-{WINDOW_MIN} minutes")).fetchone()
    return {
        "max_id": int(row["max_id"] or 0),
        "merged": int(row["merged_cnt"] or 0),
        "pr": int(row["pr_cnt"] or 0),
        "learn": int(row["learn_cnt"] or 0),
        "emp": int(row["emp_cnt"] or 0),
    }

def top_learning_titles(con: sqlite3.Connection, last_id: int, limit: int = 3):
    rows = con.execute("""
        select title
        from ceo_hub_events
        where id > ?
          and coalesce(event_type,'')='learning_result'
          and created_at >= datetime('now', ?)
        order by id desc
        limit ?
    """, (last_id, f"-{WINDOW_MIN} minutes", limit)).fetchall()
    out = []
    for r in rows:
        t = (r["title"] or "").strip()
        if t.startswith("学 習 反 映 :"):
            t = t.replace("学 習 反 映 :", "", 1).strip()
        out.append(t[:120])
    return list(reversed(out))

def top_merged_titles(con: sqlite3.Connection, last_id: int, limit: int = 2):
    rows = con.execute("""
        select title
        from ceo_hub_events
        where id > ?
          and coalesce(event_type,'')='merged'
          and created_at >= datetime('now', ?)
        order by id desc
        limit ?
    """, (last_id, f"-{WINDOW_MIN} minutes", limit)).fetchall()
    out = []
    for r in rows:
        t = (r["title"] or "").strip()
        if t.startswith("統 合 完 了 :"):
            t = t.replace("統 合 完 了 :", "", 1).strip()
        out.append(t[:120])
    return list(reversed(out))

def should_emit(c: dict) -> bool:
    return (
        c["merged"] >= MIN_MERGED
        or c["pr"] >= MIN_PR
        or c["learn"] >= MIN_LEARN
        or (c["merged"] + c["pr"] + c["learn"] + c["emp"]) >= 6
    )

def build_title(c: dict) -> str:
    merged = int(c.get("merged", 0))
    pr = int(c.get("pr", 0))
    learn = int(c.get("learn", 0))
    emp = int(c.get("emp", 0))

    if merged >= 4 and pr >= 3:
        return "OpenClaw 定 例 会 議 : 実 装 消 化 は 順 調 、 次 は 学 習 密 度 を 上 げ た い"
    if pr >= 4:
        return "OpenClaw 定 例 会 議 : PR生 成 は 強 い 、 実 装 の 流 れ は 維 持"
    if learn >= 2:
        return "OpenClaw 定 例 会 議 : 学 習 反 映 が 進 行 、 改 善 の 再 現 性 を 伸 ば し た い"
    if emp >= 1:
        return "OpenClaw 定 例 会 議 : AI社 員 側 の 更 新 あ り 、 役 割 の 固 定 化 を 観 測"
    return "OpenClaw 定 例 会 議 : 実 装 は 継 続 、 次 の 材 料 を 集 め る フ ェ ー ズ"

def build_body(c: dict, merged_titles: list[str], learn_titles: list[str]) -> str:
    from pathlib import Path
    import json

    merged = int(c.get("merged", 0))
    pr = int(c.get("pr", 0))
    learn = int(c.get("learn", 0))
    emp = int(c.get("emp", 0))

    hp = None
    phase = "自 己 強 化"
    delta_txt = "前 回 比 不 明 "
    growth = []

    try:
        hp_json = json.loads(Path("obs/company_health_score.json").read_text(encoding="utf-8"))
        hp = int(hp_json.get("maturity_percent", 0))
    except:
        hp = None

    try:
        state_path = Path("data/ai_meeting_digest_v1.state")
        if state_path.exists():
            prev = json.loads(state_path.read_text(encoding="utf-8"))
            prev_hp = int(prev.get("last_maturity_percent", hp if hp is not None else 0))
            if hp is not None:
                diff = hp - prev_hp
                if diff > 0:
                    delta_txt = f"前 回 比 +{diff}%"
                elif diff < 0:
                    delta_txt = f"前 回 比 {diff}%"
                else:
                    delta_txt = "前 回 比 ±0%"
    except:
        pass

    if hp is not None:
        if hp >= 85:
            phase = "実 運 用 直 前"
        elif hp >= 60:
            phase = "事 業 準 備"
        else:
            phase = "自 己 強 化"

    if merged >= 4:
        growth.append("実 装 消 化")
    if pr >= 4:
        growth.append("PR生 成")
    if learn >= 2:
        growth.append("学 習 反 映")
    if emp >= 1:
        growth.append("AI社 員 側")

    merged_line = "、 ".join(merged_titles[:2]) if merged_titles else "目 立 つ 統 合 は ま だ 少 な め"
    learn_line = "、 ".join(learn_titles[:2]) if learn_titles else "今 回 は 学 習 反 映 が 少 な め"

    agenda = []
    if merged >= 4:
        agenda.append("実 装 の 消 化 速 度 は 良 好")
    elif merged >= 2:
        agenda.append("実 装 は 継 続 的 に 前 進")
    else:
        agenda.append("実 装 は 小 休 止 気 味")

    if pr >= 4:
        agenda.append("供 給 か ら PRま で の 流 れ は 強 め")
    elif pr >= 2:
        agenda.append("PR生 成 は 維 持")
    else:
        agenda.append("PR材 料 は 少 な め")

    if learn >= 2:
        agenda.append("学 習 反 映 が じ わ じ わ 積 み 上 が っ て い る")
    else:
        agenda.append("学 習 反 映 は 次 回 の 観 測 点")

    decisions = []
    decisions.append(f"直 近 の 主 な 統 合 は {merged_line}")
    decisions.append(f"学 習 側 は {learn_line}")
    if hp is not None:
        decisions.append(f"事 業 開 始 達 成 率 は {hp}% 、 フ ェ ー ズ は {phase}")

    hold = []
    if learn == 0:
        hold.append("学 習 反 映 の 厚 み は ま だ 弱 い")
    if emp == 0:
        hold.append("AI社 員 側 の 変 化 は 今 回 少 な め")
    if merged < 2 and pr < 2:
        hold.append("会 議 材 料 は や や 少 な め")

    nexts = []
    if pr >= merged:
        nexts.append("供 給 ペ ー ス を 維 持 し つ つ 学 習 側 の 密 度 を 観 測")
    else:
        nexts.append("実 装 済 み の 学 習 反 映 が 次 回 ど れ だ け 積 み 上 が る か 確 認")
    if hp is not None:
        nexts.append(f"達 成 率 {hp}% の 次 の 壁 を 越 え ら れ る か を 観 測")
    if growth:
        nexts.append(f"今 回 伸 び た 領 域 は {' / '.join(growth)}")

    lines = []
    lines.append("🧠 OpenClaw 定 例 会 議")
    lines.append("")
    lines.append("■ 今 回 の 論 点")
    for x in agenda:
        lines.append(f"・ {x}")
    lines.append("")
    lines.append("■ 決 定 事 項")
    for x in decisions:
        lines.append(f"・ {x}")
    lines.append("")
    lines.append("■ 保 留 事 項")
    if hold:
        for x in hold:
            lines.append(f"・ {x}")
    else:
        lines.append("・ 大 き な 保 留 は 少 な め")
    lines.append("")
    lines.append("■ 次 回 ま で の 観 測 点")
    for x in nexts[:3]:
        lines.append(f"・ {x}")
    lines.append("")
    lines.append(f"進 捗 率 : {hp if hp is not None else '不 明 '}% / {delta_txt}")
    return "\n".join(lines)

def main():
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    last_id = load_last_id()
    con = connect()
    try:
        c = counts_since(con, last_id)
        if c["max_id"] <= last_id:
            print("skip=no_new_events")
            return
        if recent_ai_meeting_exists(con):
            save_last_id(c["max_id"])
            print("skip=recent_ai_meeting")
            return
        if not should_emit(c):
            save_last_id(c["max_id"])
            print(f"skip=below_threshold merged={c['merged']} pr={c['pr']} learn={c['learn']} emp={c['emp']}")
            return
        merged_titles = top_merged_titles(con, last_id, 2)
        learn_titles = top_learning_titles(con, last_id, 3)
        title = build_title(c)
        body = build_body(c, merged_titles, learn_titles)
        insert_ai_meeting(con, title, body)
        save_last_id(c["max_id"])
        print(f"inserted {title}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
