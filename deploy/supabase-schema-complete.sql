-- ═══════════════════════════════════════════════════════
-- SUPABASE — Observabilidad + Tenant Policies + Vault
-- Ejecutar en: https://supabase.com/dashboard/project/rjfcmmzjlguiititkmyh/sql
-- ═══════════════════════════════════════════════════════

-- 1. service_status_logs (observabilidad)
CREATE TABLE IF NOT EXISTS service_status_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service     TEXT NOT NULL,
    status      TEXT NOT NULL,  -- 'ok', 'degraded', 'down'
    latency_ms  INT NOT NULL DEFAULT 0,
    details     JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_status_logs_service_time
    ON service_status_logs(service, created_at DESC);

-- 2. tenant_policies (50 reglas por tenant)
CREATE TABLE IF NOT EXISTS tenant_policies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL UNIQUE,
    rules       JSONB NOT NULL,
    active      BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- 3. funnel_metrics (conversion tracking)
CREATE TABLE IF NOT EXISTS funnel_metrics (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL,
    stage       TEXT NOT NULL,  -- 'visit', 'scan', 'validate', 'payment', 'recycle'
    token       TEXT,
    material    TEXT,
    cashback    INT DEFAULT 0,
    ip_address  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_funnel_tenant_stage
    ON funnel_metrics(tenant_id, stage, created_at DESC);

-- 4. Vault (pgsodium)
CREATE EXTENSION IF NOT EXISTS pgsodium;

CREATE TABLE IF NOT EXISTS secrets_vault (
    name            TEXT PRIMARY KEY,
    encrypted_key   UUID NOT NULL DEFAULT pgsodium.create_key(),
    encrypted_value BYTEA NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Función: set_secret (upsert)
CREATE OR REPLACE FUNCTION set_secret(secret_name TEXT, secret_value TEXT)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE key_id UUID := pgsodium.create_key();
BEGIN
    INSERT INTO secrets_vault (name, encrypted_key, encrypted_value)
    VALUES (secret_name, key_id, pgsodium.crypto_aead_det_encrypt(
        secret_value::BYTEA, NULL::BYTEA, key_id
    ))
    ON CONFLICT (name) DO UPDATE
    SET encrypted_value = pgsodium.crypto_aead_det_encrypt(
        secret_value::BYTEA, NULL::BYTEA,
        (SELECT encrypted_key FROM secrets_vault WHERE name = secret_name)
    ),
    updated_at = now();
END;
$$;

-- Función: get_secret
CREATE OR REPLACE FUNCTION get_secret(secret_name TEXT)
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE key_id UUID;
BEGIN
    SELECT encrypted_key INTO key_id
    FROM secrets_vault WHERE name = secret_name;

    RETURN convert_from(
        pgsodium.crypto_aead_det_decrypt(
            (SELECT encrypted_value FROM secrets_vault WHERE name = secret_name),
            NULL::BYTEA, key_id
        ),
        'UTF8'
    );
END;
$$;

-- Seguridad: restringir acceso directo
REVOKE ALL ON secrets_vault FROM PUBLIC, anon, authenticated;
REVOKE ALL ON service_status_logs FROM PUBLIC, anon;
REVOKE ALL ON tenant_policies FROM PUBLIC, anon;
REVOKE ALL ON funnel_metrics FROM PUBLIC, anon;

-- Grant service role access
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;

-- ═══════════════════════════════════════════════════════
-- SEED DATA — 50 reglas para ecocupon_cl
-- ═══════════════════════════════════════════════════════

INSERT INTO tenant_policies (tenant_id, rules) VALUES ('ecocupon_cl', '{
  "precios": {
    "price_warn_mult": 3.0,
    "price_reject_mult": 10.0,
    "min_price": 10,
    "max_price": 1000000
  },
  "reciclaje": {
    "recycle_min_weight": 0.5,
    "recycle_max_daily": 50,
    "cashback_rate_vidrio": 300,
    "cashback_rate_carton": 200,
    "cashback_rate_pet": 500,
    "cashback_rate_lata": 60,
    "cashback_rate_plastico": 250,
    "cashback_rate_organico": 50,
    "cashback_rate_electronico": 1000,
    "cashback_rate_metal": 150
  },
  "fraude": {
    "fraud_max_scans_per_hour": 10,
    "fraud_same_ip_window": 60,
    "fraud_geo_radius_km": 5,
    "fraud_score_threshold": 0.7,
    "fraud_max_daily_cashback": 50000,
    "fraud_duplicate_token_window": 300
  },
  "reputacion": {
    "reputation_initial": 1.0,
    "reputation_min": 0.1,
    "reputation_max": 2.0,
    "reputation_sandbox_penalty": 0.8,
    "reputation_increment_per_valid": 0.05,
    "reputation_decrement_per_fraud": 0.2
  },
  "alertas": {
    "alert_reject_rate": 0.25,
    "alert_sandbox_rate": 0.35,
    "alert_avg_score_min": 6.5,
    "alert_telegram_enabled": true,
    "alert_response_time_sla": 60
  },
  "pagos": {
    "payment_timeout": 300,
    "payment_max_daily": 1000000,
    "payment_min_withdraw": 5000,
    "payment_method_flow_cl": true,
    "payment_method_webpay": false
  },
  "api": {
    "api_rate_limit": 100,
    "api_burst_limit": 20,
    "api_key_rotation_days": 90
  },
  "qr": {
    "qr_ttl_hours": 24,
    "qr_max_per_user_daily": 20,
    "qr_min_cashback": 50,
    "qr_format": "alphanumeric",
    "qr_length": 16
  },
  "wallet": {
    "wallet_max_balance": 500000,
    "wallet_auto_withdraw_threshold": 100000,
    "wallet_expiry_days": 365
  },
  "tenant": {
    "tenant_name": "EcoCupon Chile",
    "tenant_currency": "CLP",
    "tenant_timezone": "America/Santiago",
    "tenant_language": "es",
    "tenant_phone_prefix": "+569"
  }
}') ON CONFLICT (tenant_id) DO NOTHING;

-- Seed secrets vault
SELECT set_secret('CLOUDFLARE_API_TOKEN', 'cfut_YixFEEBIyoZbGdNoNH4yvHSgsrhsaLox7KDNbVm5719cfc37');
SELECT set_secret('N8N_ADMIN_PASSWORD', 'SmarterN8n_2026_Secure!');
SELECT set_secret('ODOO19_MASTER_PASSWORD', 'Odoo19_Master_v+LrCj3ZdOF4');

-- ═══════════════════════════════════════════════════════
-- VERIFICATION
-- ═══════════════════════════════════════════════════════

-- Verificar tablas creadas
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Verificar tenant policies
SELECT tenant_id, jsonb_object_keys(rules) as rule_categories
FROM tenant_policies WHERE tenant_id = 'ecocupon_cl';

-- Verificar secrets
SELECT name, created_at FROM secrets_vault ORDER BY name;
