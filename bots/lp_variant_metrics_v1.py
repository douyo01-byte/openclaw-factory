import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def has_column(cur, table, column):
    rows = cur.execute(f"pragma table_info({table})").fetchall()
    return any(r[1] == column for r in rows)

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("update lp_variants set views=0, unlocks=0, score=0")

    if has_column(cur, "money_orders", "birth_place"):
        rows = cur.execute("""
        select birth_place as variant, count(*)
        from money_orders
        where birth_place in ('A','B','C')
        group by birth_place
        """).fetchall()

        for variant, cnt in rows:
            cur.execute("update lp_variants set views=? where variant=?", (cnt, variant))

        if has_column(cur, "money_deliveries", "order_id"):
            rows = cur.execute("""
            select mo.birth_place as variant, count(*)
            from money_deliveries md
            join money_orders mo on mo.id = md.order_id
            where mo.birth_place in ('A','B','C')
            group by mo.birth_place
            """).fetchall()

            for variant, cnt in rows:
                cur.execute("update lp_variants set unlocks=? where variant=?", (cnt, variant))
    else:
        print("money_orders.birth_place_missing -> metrics left at zero", flush=True)

    cur.execute("""
    update lp_variants
    set score = case
      when views > 0 then cast((unlocks * 100) / views as integer)
      else 0
    end
    """)

    con.commit()
    con.close()
    print("lp_variant_metrics_updated", flush=True)

if __name__ == "__main__":
    main()
