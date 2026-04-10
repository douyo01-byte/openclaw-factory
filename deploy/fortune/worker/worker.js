export default {
  async fetch(request, env) {
    const url = new URL(request.url)

    if (url.pathname === "/health") {
      return Response.json({ ok: true })
    }

    if (url.pathname === "/order" && request.method === "POST") {
      const form = await request.formData()

      const payload = {
        plan: form.get("plan") || "簡易鑑定",
        customer_name: form.get("customer_name") || "",
        birth_date: form.get("birth_date") || "",
        birth_time: form.get("birth_time") || "",
        birth_place: form.get("birth_place") || "",
        question: form.get("question") || "",
        email: form.get("email") || "",
        trial_id: env.TRIAL_ID || "1",
        received_at: new Date().toISOString()
      }

      return Response.json({
        status: "ok",
        message: "worker received order payload",
        payload
      })
    }

    return new Response("Not found", { status: 404 })
  }
}
