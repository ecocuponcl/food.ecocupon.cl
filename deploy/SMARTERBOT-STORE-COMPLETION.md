# BOLT AGENT — SmarterBOT Store Completion

## 🎯 Misión
Completar el deploy de SmarterBOT Store para que sea 100% funcional y accesible.

## 📁 Contexto
Brief completo: /Users/mac/dev/2026/food.ecocupon.cl/deploy/SMARTERBOT-STORE-BRIEF.md
Landing files: /Users/mac/dev/2026/food.ecocupon.cl/landing-store/ (6 files, ya creadas)

## ✅ Ya hecho
- 6 archivos HTML/CSS/JS creados
- DNS store.ecocupon.cl → 89.116.23.167 (Cloudflare)
- Caddy route configurada
- Files uploaded a VPS /var/www/smarterbot-store/
- Affiliate links: ?REFERRALCODE=SMARTER

## 🔴 Problemas Actuales

### 1. SSL 525 en store.ecocupon.cl
- Cloudflare no puede validar el cert
- Verificar: `curl -sI https://store.ecocupon.cl/` → 525
- Caddy en VPS sí responde (308 a HTTPS)

### 2. smarterbot.store sigue en Vercel
- DNS: 216.198.79.1 (Vercel)
- Necesita migrar a Cloudflare o usar store.ecocupon.cl

### 3. Formularios sin conexión a n8n
- Form cotización en clawbot.html → no envía
- Form contacto → sin webhook

## 📋 Tareas Delegables

### TAREA 1: Fix SSL store.ecocupon.cl
1. SSH a VPS root@89.116.23.167
2. Verificar Caddy: `cat /etc/caddy/Caddyfile | grep -A 5 store`
3. Forzar cert: `caddy reload /etc/caddy/Caddyfile`
4. Esperar 5 min, verificar: `curl -sI https://store.ecocupon.cl/`
5. Si sigue 525, probar con Cloudflare dev mode

### TAREA 2: Conectar formularios a n8n webhook
1. Crear webhook en n8n: POST endpoint que reciba {name, email, phone, message, service}
2. Actualizar js/main.js para POST al webhook
3. Webhook → Odoo CRM lead creation (ya existe pipeline)
4. Test: enviar form → verificar en n8n execution log

### TAREA 3: smarterbot.store → redirect a store.ecocupon.cl
Opción A: Crear Cloudflare Page Rule para redirect
Opción B: Agregar Caddy route para smarterbot.store → redirect
Opción C: DNS update via API si smarterbot.store está en Cloudflare

### TAREA 4: Testing completo
1. `curl -sI https://store.ecocupon.cl/` → 200
2. `curl -s https://store.ecocupon.cl/` → HTML completo
3. `curl -s https://store.ecocupon.cl/hosting.html` → 200
4. `curl -s https://store.ecocupon.cl/clawbot.html` → 200
5. `curl -s https://store.ecocupon.cl/kiosk.html` → 200
6. Mobile: viewport correcto, nav responsive
7. Links afiliados: todos incluyen ?REFERRALCODE=SMARTER

### TAREA 5: SEO + Analytics básico
1. Agregar meta tags OG (Open Graph) a cada página
2. Sitemap.xml básico
3. robots.txt
4. Favicon (puede ser emoji 🟡⚫)

## 🔑 Creds Disponibles

| Servicio | Detalle |
|----------|---------|
| Cloudflare API | cfut_YixFEEBIyoZbGdNoNH4yvHSgsrhsaLox7KDNbVm5719cfc37 |
| Zone ecocupon.cl | 3bdf9d7aa5344207b73d4f29043027d4 |
| VPS SSH | root@89.116.23.167 |
| n8n | https://n8n.smarterbot.store (auth: admin/SmarterN8n_2026_Secure!) |
| Hostinger affiliate | ?REFERRALCODE=SMARTER |

## 📊 Criterios de Éxito

| Check | Pass |
|-------|------|
| store.ecocupon.cl → 200 HTTPS | ✅ |
| 4 páginas cargan completo | ✅ |
| Links afiliados correctos | ✅ |
| Form envía a n8n | ✅ |
| Mobile responsive | ✅ |
| SEO meta tags | ✅ |

## 🚀 Execute
Start with TAREA 1 (SSL fix), then proceed sequentially.
Report all changes made and final verification results.
