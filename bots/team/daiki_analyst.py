import sqlite3,random,math
conn=sqlite3.connect("data/openclaw.db")
c=conn.cursor()
rows=c.execute("select id,title from items where id not in (select item_id from opportunity_plan)").fetchall()
for item_id,title in rows:
    price=random.randint(2980,4980)
    cogs=int(price*0.30)
    ship=450
    duty=150
    fee=12
    ads=300
    other=100
    units=random.randint(40,120)
    c.execute("""insert or replace into opportunity_plan
    (item_id,product_name,target_price_jpy,est_cogs_jpy,ship_jpy,duty_vat_jpy,platform_fee_pct,ads_cac_jpy,returns_pct,other_jpy,est_units_month)
    values(?,?,?,?,?,?,?,?,?,?,?)""",
    (item_id,title,price,cogs,ship,duty,fee,ads,3,other,units))
conn.commit()
