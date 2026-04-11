# Odoo Website Theme — SmarterKiosk (MeliNinja Style)

## Instalación en Odoo

1. **Log in** → https://odoo.ecocupon.cl/web/login
   - User: `admin`
   - Pass: `SmarterOS2026!`

2. **Ir a Sitio Web** → Editor

3. **Crear tema personalizado:**
   - Ir a `Sitio Web` → `Configuración` → `Tema`
   - Copiar el CSS personalizado desde el archivo `theme.css`
   - Aplicar colores: Amarillo (#FFF159), Azul (#3483FA), Verde (#00A650)

## Estructura del sitio (basado en melininja.com)

```
HEADER
  - Logo "SmarterKiosk"
  - Barra de búsqueda
  - Iconos: WhatsApp | Telegram | Carrito

HERO SECTION
  - "Automatiza tu Negocio con Kiosks de Autoservicio"
  - CTA: "Ver Kiosks Disponibles"
  - Badges: ⚡48hs | 🔧24/7 | 💳Pagos | 📊Dashboard

SECCIONES:
  1. ¿Qué es SmarterKiosk? (3 cards con iconos)
  2. Productos (grid de 6 productos estilo ML)
  3. ¿Qué incluye? (módulos expandibles)
  4. Bonus (lista con iconos)
  5. Si sigues las instrucciones (outcomes)
  6. Pricing card (precio destacado)
  7. FAQ (accordion)
  8. CTA Final
  9. Footer

FOOTER
  - Links: Odoo | n8n | Dashboard | API
  - WhatsApp: +56979540471
  - Telegram: @SmarterKiosk

BOTONES FLOTANTES:
  - WhatsApp (verde, esquina inferior derecha)
  - Telegram (azul, al lado de WhatsApp)
```

## CSS Personalizado

Colores MeliNinja:
- Amarillo header: #FFF159
- Azul botones: #3483FA
- Verde éxito: #00A650
- Fondo: #EBEBEB
- Texto: #333

## WhatsApp + Telegram

```html
<!-- WhatsApp flotante -->
<a href="https://wa.me/56979540471?text=Hola!%20Me%20interesa%20un%20CLAWBOT%20Kiosk" 
   class="social-float whatsapp" target="_blank">💬</a>

<!-- Telegram flotante -->
<a href="https://t.me/SmarterKiosk" 
   class="social-float telegram" target="_blank">✈️</a>
```

## One-Click Checkout

En Odoo:
1. Ir a `eCommerce` → `Configuración`
2. Activar "One-Page Checkout"
3. Desactivar pasos innecesarios
4. Configurar MercadoPago como pasarela

## Pasos para aplicar en Odoo

1. Ir a `Sitio Web` → `Editor`
2. Click en `Tema` → `CSS personalizado`
3. Pegar contenido de `theme.css`
4. Agregar HTML de secciones en `Páginas` → `Inicio`
5. Configurar productos con precios en CLP
6. Activar checkout de una página
7. Agregar botones flotantes de WhatsApp y Telegram
