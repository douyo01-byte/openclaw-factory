import os,sqlite3,datetime,requests

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
FACTORY_DB=os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
TOKEN=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def dconn():
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def fconn():
    c=sqlite3.connect(FACTORY_DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def tg_send(chat_id,text):
    r=requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":str(chat_id),"text":text},
        timeout=20,
    )
    r.raise_for_status()

def one(c,q,a=()):
    r=c.execute(q,a).fetchone()
    return r[0] if r else 0

def label_latest(status,spec_stage,dev_stage):
    if status=="merged" or dev_stage=="merged":
        return "統合済み"
    if status in ("open","pr_created") or dev_stage in ("open","pr_created","executed"):
        return "開発中"
    if spec_stage=="refined":
        return "仕様整理済み"
    if status=="approved":
        return "承認済み"
    return "進行中"

def summarize_hub_title(title):
    t=(title or "").strip()
    if t.startswith("AI会議結果"):
        return "AI会議を実施しました"
    if t.startswith("詳しい解説 #"):
        return t.replace("詳しい解説","案件の詳しい報告")
    if t.startswith("案件報告 #"):
        return t.replace("案件報告","案件の進捗報告")
    return t or "新しい更新があります"

def latest_summary(status,spec_stage,dev_stage):
    if status=="merged" or dev_stage=="merged":
        return "実装から統合まで完了しています"
    if status in ("open","pr_created") or dev_stage in ("open","pr_created","executed"):
        return "現在は開発またはPR確認が進行中です"
    if spec_stage=="refined":
        return "仕様整理が終わり、開発に渡せる状態です"
    if status=="approved":
        return "承認済みで次工程待ちです"
    return "現在進行中です"

def team_and_bot(name):
    n=(name or "")
    if "スカウト" in n or "調査" in n or "企画" in n:
        return "事業チーム", "SekawakuClaw_bot"
    if "設計" in n or "エンジニア" in n or "監査" in n or "統合" in n:
        return "開発チーム", "Kaikun01_bot"
    if "報告" in n or "秘書" in n:
        return "経営共有チーム", "Kaikun02_bot"
    return "共通チーム", "-"

def build_text():
    with dconn() as d, fconn() as f:
        emp_rows=d.execute("""
            select display_name, role_name
            from ai_employees
            where is_enabled=1
            order by id asc
        """).fetchall()

        total_props=one(f,"select count(*) from dev_proposals")
        approved=one(f,"select count(*) from dev_proposals where coalesce(status,'')='approved'")
        refined=one(f,"select count(*) from dev_proposals where coalesce(spec_stage,'')='refined'")
        executing=one(f,"select count(*) from dev_proposals where coalesce(dev_stage,'') in ('executed','pr_created','open')")
        merged=one(f,"select count(*) from dev_proposals where coalesce(status,'')='merged' or coalesce(dev_stage,'')='merged'")
        waiting_answer=one(f,"select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'")
        answer_received=one(f,"select count(*) from proposal_state where coalesce(stage,'')='answer_received'")
        pr_open=one(f,"select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
        pr_merged=one(f,"select count(*) from dev_proposals where coalesce(pr_status,'')='merged'")

        recent=f.execute("""
            select id,title,coalesce(status,''),coalesce(spec_stage,''),coalesce(dev_stage,'')
            from dev_proposals
            order by id desc
            limit 5
        """).fetchall()

        hub_recent=d.execute("""
            select title
            from ceo_hub_events
            order by id desc
            limit 5
        """).fetchall()

    business=[]
    development=[]
    executive=[]

    for r in emp_rows:
        team,bot=team_and_bot(r["display_name"])
        line=f"- {r['display_name']} / {r['role_name']}"
        if team=="事業チーム":
            business.append(line)
        elif team=="開発チーム":
            development.append(line)
        else:
            executive.append(line)

    lines=[
        "【OpenClaw 経営ダッシュボード】",
        f"時刻: {now()}",
        "",
        "【海外貿易事業チーム】SekawakuClaw_bot",
    ]
    lines.extend(business or ["- まだ未設定"])

    lines.extend([
        "",
        "【開発チーム】Kaikun01_bot",
    ])
    lines.extend(development or ["- まだ未設定"])

    lines.extend([
        "",
        "【経営共有チーム】Kaikun02_bot",
    ])
    lines.extend(executive or ["- まだ未設定"])

    lines.extend([
        "",
        "【案件の全体像】",
        f"- これまでの総案件数: {total_props}",
        f"- 承認済みで次工程待ち: {approved}",
        f"- 仕様が固まり開発へ渡せる案件: {refined}",
        f"- 今まさに開発やPR確認が進んでいる案件: {executing}",
        f"- 統合まで完了した案件: {merged}",
        "",
        "【社長の返答が関係する項目】",
        f"- いま返答待ちの仕様確認: {waiting_answer}",
        f"- 返答は受け取ったが後続処理中: {answer_received}",
        "",
        "【GitHubの状況】",
        f"- まだ開いているPR: {pr_open}",
        f"- マージ済みPR: {pr_merged}",
        "",
        "【今日の主な動き】",
    ])

    if hub_recent:
        lines.append(f"- 今日の更新件数: {len(hub_recent)}件")
        lines.append("- 要約: AI会議・案件報告・詳しい解説が更新されています")
        for r in hub_recent:
            lines.append(f"  ・{summarize_hub_title(r['title'])}")
    else:
        lines.append("- まだ新しい共有はありません")

    lines.extend([
        "",
        "【直近の案件】",
    ])

    for r in recent:
        lines.append(f"- #{r['id']} {r['title']} / {label_latest(r[2],r[3],r[4])}")
        lines.append(f"  {latest_summary(r[2],r[3],r[4])}")

    lines.extend([
        "",
        "【社長への相談・共有事項】",
        "- 返答待ちの仕様確認が増えたら優先判断が必要です",
        "- 開発中案件が統合待ちで滞留していないか見てください",
        "- 詳しい経緯が必要な案件は Kaikun03 側で長文報告する形に広げる予定です",
        "",
        "【使えるCEOコマンド】",
        "/company",
        "/meeting <議題>",
        "/help",
    ])

    return "\n".join(lines)

def run_once():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN empty")

    done=0
    with dconn() as d:
        rows=d.execute("""
            select id,chat_id,text
            from inbox_commands
            where coalesce(processed,0)=0
              and trim(coalesce(text,''))='/company'
            order by id asc
            limit 5
        """).fetchall()

        for r in rows:
            try:
                tg_send(r["chat_id"], build_text())
                d.execute(
                    "update inbox_commands set processed=1,status='company_done',applied_at=? where id=?",
                    (now(), int(r["id"]))
                )
            except Exception as e:
                d.execute(
                    "update inbox_commands set status='company_error', error=?, applied_at=? where id=?",
                    (repr(e), now(), int(r["id"]))
                )
            d.commit()
            done+=1

    print(f"company_done={done}", flush=True)

if __name__=="__main__":
    run_once()

def humanize_title(title):
    t=(title or "").strip()

    if "AI会議結果" in t:
        return "AI会議を実施し、今後の事業方針を議論しました"

    if "詳しい解説" in t:
        num=t.split("#")[-1]
        return f"案件{num}についてAIが詳しい技術解説を作成しました"

    if "案件報告" in t:
        num=t.split("#")[-1]
        return f"案件{num}の進行状況をAIがまとめました"

    return t
