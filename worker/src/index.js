export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    if (url.pathname === "/health") {
      return new Response(JSON.stringify({
        status: "ok",
        service: "ecocupon-ai-agent",
        model: "@cf/meta/llama-3-8b-instruct"
      }), { headers: { "Content-Type": "application/json" } });
    }

    if (url.pathname === "/decide" && request.method === "POST") {
      const body = await request.json();
      
      const prompt = `Eres EcoCupon AI. Decide sobre: ${JSON.stringify(body)}`;
      
      const response = await env.AI.run("@cf/meta/llama-3-8b-instruct", {
        messages: [{ role: "user", content: prompt }],
        max_tokens: 500
      });

      return new Response(JSON.stringify({
        vertical: body.vertical || "unknown",
        decision: response.response?.trim() || "no response",
        model: "@cf/meta/llama-3-8b-instruct"
      }), { headers: { "Content-Type": "application/json" } });
    }

    return new Response(JSON.stringify({
      service: "EcoCupon AI Agent",
      endpoints: ["/health", "/decide"],
      docs: "POST /decide with {vertical, data}"
    }), { headers: { "Content-Type": "application/json" } });
  }
};
