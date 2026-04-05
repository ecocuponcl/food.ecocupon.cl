export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    if (url.pathname === "/health") {
      return new Response(JSON.stringify({
        status: "ok",
        service: "ecocupon-ai-agent",
        model: "@cf/meta/llama-3-8b-instruct",
        prompt: "unified"
      }), { headers: { "Content-Type": "application/json" } });
    }

    if (url.pathname === "/decide" && request.method === "POST") {
      const body = await request.json();
      
      const systemPrompt = body.system_prompt || "Eres EcoCupon AI — asistente de ventas y reciclaje. Ayuda con: 1) Pedidos kiosco, 2) Reciclaje con cashback, 3) Valuación vehículos. Responde conciso en español (máx 3 oraciones).";
      
      const userPrompt = `Data: ${JSON.stringify(body.data || body)}`;
      
      const response = await env.AI.run("@cf/meta/llama-3-8b-instruct", {
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        max_tokens: 500
      });

      return new Response(JSON.stringify({
        vertical: body.vertical || "unknown",
        decision: response.response?.trim() || "no response",
        model: "@cf/meta/llama-3-8b-instruct",
        source: "cloudflare"
      }), { headers: { "Content-Type": "application/json" } });
    }

    return new Response(JSON.stringify({
      service: "EcoCupon AI Agent",
      endpoints: ["/health", "/decide"],
      docs: "POST /decide with {vertical, data, system_prompt}"
    }), { headers: { "Content-Type": "application/json" } });
  }
};
