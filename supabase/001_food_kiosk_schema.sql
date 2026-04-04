-- Food Kiosk EcoCupon — Supabase Migration
-- Run in Supabase Dashboard → SQL Editor
-- Project: https://rjfcmmzjlguiititkmyh.supabase.co

-- ── Orders (kiosk orders linked to Odoo) ──
CREATE TABLE IF NOT EXISTS food_kiosk_orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id TEXT DEFAULT 'ecocupon',
    order_ref TEXT UNIQUE NOT NULL,
    odoo_order_id INTEGER,
    amount INTEGER,
    status TEXT DEFAULT 'draft',
    flow_token TEXT,
    flow_url TEXT,
    customer_name TEXT,
    customer_email TEXT,
    payment_status TEXT DEFAULT 'pending',
    paid_at TIMESTAMPTZ,
    dte_status TEXT DEFAULT 'not_generated',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Payments (Flow.cl payment tracking) ──
CREATE TABLE IF NOT EXISTS food_kiosk_payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id UUID REFERENCES food_kiosk_orders(id),
    tenant_id TEXT DEFAULT 'ecocupon',
    flow_cl_token TEXT,
    flow_cl_url TEXT,
    amount INTEGER,
    currency TEXT DEFAULT 'CLP',
    status TEXT DEFAULT 'pending',
    payment_method TEXT,
    buyer_email TEXT,
    webhook_received_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── DTE (Chilean digital invoices) ──
CREATE TABLE IF NOT EXISTS food_kiosk_dte (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id UUID REFERENCES food_kiosk_orders(id),
    tenant_id TEXT DEFAULT 'ecocupon',
    dte_type INTEGER DEFAULT 39,  -- Boleta electrónica
    dte_folio INTEGER,
    sii_status TEXT DEFAULT 'not_sent',
    dte_xml TEXT,
    dte_track_id TEXT,
    dte_received TEXT,
    rut_emisor TEXT DEFAULT '78233417-4',
    rut_receptor TEXT,
    monto_total INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Events (CRM event log) ──
CREATE TABLE IF NOT EXISTS food_kiosk_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id TEXT DEFAULT 'ecocupon',
    order_id UUID REFERENCES food_kiosk_orders(id),
    event_type TEXT NOT NULL,
    source TEXT,  -- kiosk, chatwoot, webhook, n8n
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes for performance ──
CREATE INDEX IF NOT EXISTS idx_fko_tenant ON food_kiosk_orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_fko_status ON food_kiosk_orders(status);
CREATE INDEX IF NOT EXISTS idx_fkp_order ON food_kiosk_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_fke_type ON food_kiosk_events(event_type);
CREATE INDEX IF NOT EXISTS idx_fkf_status ON food_kiosk_payments(status);

-- ── Sample data ──
INSERT INTO food_kiosk_orders (order_ref, odoo_order_id, amount, status)
VALUES ('KO-000001', 37, 9990, 'confirmed')
ON CONFLICT (order_ref) DO NOTHING;

-- ── Existing tables already cover: ──
-- tenants (46 tables exist including tenants, users, clients, contracts, payments, messages, events)
-- See: https://rjfcmmzjlguiititkmyh.supabase.co/dashboard/editor
