import os,sqlite3,requests,time,re

DB=os.environ["DB_PATH"]
TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
CHAT=os.environ["TELEGRAM_CHAT_ID"]

MAX_LEN=3500

def clean_text(s):
    return (s or "").replace("\x00"," ").strip()

def jaify_keep_long_spec(s):
    s=clean_text(s)

    reps=[
        ("Development Specification for", "開発仕様書:"),
        ("Goal:", "目的:"),
        ("Scope:", "対象範囲:"),
        ("Behavior:", "想定動作:"),
        ("Inputs/Outputs:", "入力 / 出力:"),
        ("Inputs:", "入力:"),
        ("Outputs:", "出力:"),
        ("Edge Cases:", "注意点:"),
        ("Logging Policy:", "ログ方針:"),
        ("Files to Change:", "変更対象ファイル:"),
        ("Acceptance Criteria:", "受け入れ条件:"),

        ("Develop a command-line interface (CLI) tool", "コマンドラインインターフェース（CLI）ツールを開発する"),
        ("that enables users to manage", "ユーザーが管理できるようにする"),
        ("efficiently from the terminal.", "ターミナルから効率よく扱えるようにする。"),
        ("The CLI will support functionalities such as", "CLIは次の機能をサポートする:"),
        ("project creation", "案件作成"),
        ("deployment management", "デプロイ管理"),
        ("team collaboration features", "チーム連携機能"),
        ("real-time updates on project status", "案件状況のリアルタイム更新"),
        ("Users can create, list, and manage projects.", "ユーザーは案件の作成・一覧表示・管理ができる。"),
        ("Users can deploy applications and view deployment statuses.", "ユーザーはアプリをデプロイし、状態を確認できる。"),
        ("Users can collaborate with team members", "ユーザーはチームメンバーと連携できる"),
        ("The CLI will provide real-time updates", "CLIはリアルタイム更新を提供する"),
        ("Command-line arguments for project management", "案件管理用のコマンドライン引数"),
        ("user credentials for authentication", "認証用ユーザー情報"),
        ("configuration files", "設定ファイル"),
        ("Console messages indicating success or failure of commands", "コマンド成功・失敗を示すコンソール出力"),
        ("formatted lists of projects and deployments", "案件とデプロイの整形済み一覧"),
        ("Handle invalid commands gracefully with user-friendly error messages.", "不正なコマンドでも分かりやすいエラーメッセージで処理する。"),
        ("Ensure proper authentication and authorization checks are in place.", "適切な認証・権限確認を行う。"),
        ("Manage network failures during deployment and provide retry options.", "デプロイ中の通信失敗に対応し、再試行手段を用意する。"),
        ("Validate input data formats and provide clear feedback on errors.", "入力形式を検証し、エラー時は明確に返す。"),
        ("Implement logging for all CLI commands executed", "実行されたCLIコマンドをすべて記録する"),
        ("Log errors and exceptions with stack traces for debugging purposes.", "エラーや例外はデバッグ用にスタックトレース付きで記録する。"),
        ("Maintain a separate log file for real-time updates and notifications.", "リアルタイム更新や通知用のログを分けて保持する。"),
        ("Create a new CLI module", "新しいCLIモジュールを作成する"),
        ("Update the project management module", "案件管理モジュールを更新する"),
        ("Modify the deployment module", "デプロイモジュールを更新する"),
        ("Update documentation files", "ドキュメントを更新する"),
        ("The CLI tool must allow users to create and manage projects without errors.", "CLIツールは案件の作成・管理をエラーなく行えること。"),
        ("Real-time updates must reflect accurately in the terminal.", "リアルタイム更新がターミナルに正しく反映されること。"),
        ("All commands must return appropriate success or error messages.", "すべてのコマンドが適切な成功・失敗メッセージを返すこと。"),
        ("The tool must log all actions and errors as specified.", "仕様どおりに操作とエラーを記録すること。"),
        ("User documentation must be clear and comprehensive, covering all CLI functionalities.", "利用者向けドキュメントが明確で、CLI機能を十分に網羅していること。"),
    ]

    for a,b in reps:
        s=s.replace(a,b)

    s=re.sub(r'\*\*([^*]+)\*\*', r'【\1】', s)
    s=re.sub(r'\n{3,}', '\n\n', s)
    return s

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":CHAT,"text":msg},
        timeout=20
    ).raise_for_status()

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row

    rows=conn.execute("""
    SELECT
      ps.proposal_id AS id,
      d.title AS title,
      coalesce(d.spec,'') AS spec,
      coalesce(ps.pending_question,'') AS pending_question
    FROM proposal_state ps
    LEFT JOIN dev_proposals d ON d.id=ps.proposal_id
    WHERE ps.stage='refined'
      AND coalesce(ps.notified_at,'')=''
    ORDER BY ps.proposal_id ASC
    """).fetchall()

    print(f"rows={len(rows)}", flush=True)

    for r in rows:
        body=r["spec"] if (r["spec"] or "").strip() else r["pending_question"]
        title=clean_text(r["title"] or "(no title)")
        body=jaify_keep_long_spec(body)

        head=f"🧠 仕様確認\nID:{r['id']}\n案件:{title}\n\n"
        room=MAX_LEN-len(head)
        if room < 100:
            room=100
        msg=head + body[:room]

        try:
            send(msg)
            conn.execute(
                "update proposal_state set notified_at=datetime('now') where proposal_id=?",
                (r["id"],)
            )
            conn.commit()
            print(f"sent id={r['id']}", flush=True)
        except Exception as e:
            print(f"failed id={r['id']} err={e}", flush=True)

    conn.close()

if __name__=="__main__":
    while True:
        run()
        time.sleep(20)
