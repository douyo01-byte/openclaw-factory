function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  })
}

function buildFreeResult(question, name) {
  const q = (question || "").toLowerCase()
  let summary = "相手はまだ完全に気持ちが離れているわけではありません。"
  let next = "ただし、今のまま動かなければ関係は自然消滅に向かう可能性があります。"

  if (q.includes("復縁")) {
    summary = "相手との縁はまだ切れていません。"
    next = "ただし、焦って接触すると逆効果になる可能性があります。"
  } else if (q.includes("連絡")) {
    summary = "今は連絡の内容より、タイミングのほうが重要です。"
    next = "押しすぎると距離が開きやすい流れです。"
  } else if (q.includes("片思い")) {
    summary = "相手はあなたを意識する余地があります。"
    next = "ただし、今は強いアピールより自然な接点が有効です。"
  }

  return {
    title: `${name || "あなた"}の無料診断結果`,
    summary,
    next,
    paid_preview: "この続きでは、相手の本音、今やるべき行動3つ、NG行動3つを表示します。"
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url)

    if (url.pathname === "/health") {
      return json({ ok: true })
    }

    if (url.pathname === "/variant_metrics") {
      const viewsRes = await env.DB.prepare(`
        select birth_place as variant, count(*) as views
        from public_orders
        where birth_place in ('A','B','C','D')
        group by birth_place
      `).all()

      const unlocksRes = await env.DB.prepare(`
        select o.birth_place as variant, count(*) as unlocks
        from public_unlocks u
        join public_orders o on o.id = u.order_id
        where o.birth_place in ('A','B','C','D')
        group by o.birth_place
      `).all()

      const map = {
        A: { views: 0, unlocks: 0 },
        B: { views: 0, unlocks: 0 },
        C: { views: 0, unlocks: 0 },
        D: { views: 0, unlocks: 0 },
        D: { views: 0, unlocks: 0 }
      }

      for (const r of (viewsRes.results || [])) {
        if (map[r.variant]) map[r.variant].views = Number(r.views || 0)
      }

      for (const r of (unlocksRes.results || [])) {
        if (map[r.variant]) map[r.variant].unlocks = Number(r.unlocks || 0)
      }

      return json(map)
    }

    if (url.pathname === "/order" && request.method === "POST") {
      const form = await request.formData()

      const payload = {
        plan: String(form.get("plan") || "簡易鑑定").trim(),
        customer_name: String(form.get("customer_name") || "").trim(),
        birth_date: String(form.get("birth_date") || "").trim(),
        birth_time: String(form.get("birth_time") || "").trim(),
        birth_place: String(form.get("birth_place") || "").trim(),
        question: String(form.get("question") || "").trim(),
        email: String(form.get("email") || "").trim(),
        variant: String(form.get("variant") || "A").trim()
      }

      if (!payload.customer_name || !payload.birth_date || !payload.question || !payload.email) {
        return json({ status: "error", message: "required fields missing" }, 400)
      }

      const now = new Date().toISOString()

      const result = await env.DB.prepare(`
        insert into public_orders
        (plan, customer_name, birth_date, birth_time, birth_place, question, email, created_at)
        values (?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        payload.plan,
        payload.customer_name,
        payload.birth_date,
        payload.birth_time,
        payload.birth_place,
        payload.question,
        payload.email,
        now
      ).run()

      await env.DB.prepare(`
        update public_orders
        set birth_place = ?
        where id = ?
      `).bind(payload.variant, result.meta.last_row_id).run()

      const orderId = result.meta.last_row_id
      const freeResult = buildFreeResult(payload.question, payload.customer_name)

      return json({
        status: "ok",
        order_id: orderId,
        variant: payload.variant,
        free_result: freeResult
      })
    }

    if (url.pathname === "/unlock" && request.method === "POST") {
      const body = await request.json().catch(() => ({}))
      const orderId = Number(body.order_id || 0)

      if (!orderId) {
        return json({ status: "error", message: "order_id required" }, 400)
      }

      const now = new Date().toISOString()

      await env.DB.prepare(`
        insert into public_unlocks (order_id, price_yen, status, created_at)
        values (?, 760, 'pending', ?)
      `).bind(orderId, now).run()

      return json({
        status: "ok",
        order_id: orderId,
        unlock_status: "pending",
        message: "760円解放リクエストを保存しました"
      })
    }

    if (url.pathname === "/orders" && request.method === "GET") {
      const rows = await env.DB.prepare(`
        select id, customer_name, plan, email, birth_place, created_at
        from public_orders
        order by id desc
        limit 20
      `).all()

      return json(rows)
    }

    if (url.pathname === "/unlocks" && request.method === "GET") {
      const rows = await env.DB.prepare(`
        select id, order_id, price_yen, status, created_at
        from public_unlocks
        order by id desc
        limit 20
      `).all()

      return json(rows)
    }

    return new Response("Not found", { status: 404 })
  }
}
