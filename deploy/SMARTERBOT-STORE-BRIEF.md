# BOLT AGENT — SmarterBOT Store Landing Page

## 🎯 Misión
Crear landing page completa para **smarterbot.store** con 3 pilares:

1. **🌐 HOSTING** → Afiliados Hostinger (link: ?REFERRALCODE=SMARTER)
2. **🤖 CLAWBOT** → Servicio implementación kiosks a medida (25 UF/mes)
3. **🛒 KIOSK** → Productos QR + Flow.cl + MercadoLibre

## 📁 Stack
- **HTML/CSS/JS vanilla** (no frameworks, rápido)
- **Responsive** (mobile-first)
- **Dark theme** (🟡⚫ brand: #FFD700 + #000000)
- **Font**: Inter + JetBrains Mono
- **Deploy**: `/var/www/smarterbot-store/` en VPS
- **Caddy route**: `smarterbot.store` → `/var/www/smarterbot-store`

## 🏗️ Estructura

```
/var/www/smarterbot-store/
├── index.html           ← Landing principal (3 pilares)
├── hosting.html         ← Catálogo Hostinger (afiliados)
├── clawbot.html         ← Servicio CLAWBOT (cotización)
├── kiosk.html           ← Tienda kiosk QR + Flow.cl
├── css/
│   └── style.css        ← Brand + responsive
└── js/
    └── main.js          ← Navigation + interactions
```

## 🎨 Diseño

### Hero Section
```
┌──────────────────────────────────────────┐
│  🟡⚫ SmarterBOT Store                    │
│  "Tu negocio digital, de principio a fin" │
│                                          │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ 🌐      │ │ 🤖      │ │ 🛒        │  │
│  │ HOSTING │ │ CLAWBOT │ │ KIOSK     │  │
│  │         │ │         │ │           │  │
│  │ Hosting │ │ Kiosks  │ │ QR +      │  │
│  │ VPS     │ │ a medida│ │ Flow.cl   │  │
│  │ Email   │ │ 25 UF   │ │ ML        │  │
│  └─────────┘ └─────────┘ └───────────┘  │
│                                          │
│  [Comenzar →]                            │
└──────────────────────────────────────────┘
```

### Hosting Page (Afiliados)
Productos con links `?REFERRALCODE=SMARTER`:
- Web Hosting ($2.99/mes → link)
- Cloud Hosting ($7.99/mes → link)
- VPS Hosting ($4.99/mes → link)
- WordPress Hosting ($2.99/mes → link)
- Email Hosting ($0.99/mes → link)
- Dominios (.cl → link)

### CLAWBOT Page (Servicio)
- "Te hacemos tu kiosk personalizado"
- Features: Templates por tenant, branding custom, Flow.cl, Odoo
- Proceso: Cotización → Contrato → Deploy
- CTA: "Solicitar cotización" → form → n8n webhook

### Kiosk Page (Tienda QR)
- Escanear → Cashback instantáneo
- Flow.cl para cobros
- MercadoLibre sync
- Productos con código QR EcoCupon
- CTA: "Ver productos" / "Solicitar kiosk"

## 🔗 Links Afiliados Hostinger
Base URL: `https://www.hostinger.com/es?REFERRALCODE=SMARTER`

## 📧 Lead Capture
Formulario en cada página → POST a n8n webhook → Odoo CRM

## 📊 Métricas
- `/status.json` ya existe en `os.smarterbot.store`
- No interferir con rutas existentes

## ✅ Checkpoint
Cuando termines:
1. Upload a VPS `/var/www/smarterbot-store/`
2. Add Caddy route: `smarterbot.store { root * /var/www/smarterbot-store; encode gzip; file_server }`
3. Verify: `curl -sI https://smarterbot.store/` → 200
4. All pages load, mobile responsive
