-- EcoCupon Supabase Schema
-- Run in Supabase SQL Editor

-- ── Event Log (everything passes through here) ────────
CREATE TABLE IF NOT EXISTS events_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,           -- agent, flow, odoo, n8n
  type TEXT NOT NULL,             -- decide.recycle, decide.vehicle, webhook, etc.
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_log_source ON events_log(source);
CREATE INDEX idx_events_log_type ON events_log(type);
CREATE INDEX idx_events_log_created ON events_log(created_at);

-- ── Wallets ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wallets (
  phone TEXT PRIMARY KEY,
  balance INT DEFAULT 0,
  total_earned INT DEFAULT 0,
  total_recycled INT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Recycle Events (with idempotency) ─────────────────
CREATE TABLE IF NOT EXISTS recycle_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT UNIQUE NOT NULL,  -- idempotency key
  phone TEXT NOT NULL REFERENCES wallets(phone),
  item TEXT NOT NULL,
  reward INT NOT NULL,
  validation_type TEXT,           -- photo, gps, truck
  photo_url TEXT,
  lat FLOAT,
  lng FLOAT,
  fraud_score FLOAT DEFAULT 0,
  status TEXT DEFAULT 'pending',  -- pending | approved | rejected
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recycle_phone ON recycle_events(phone);
CREATE INDEX idx_recycle_created ON recycle_events(created_at);
CREATE INDEX idx_recycle_status ON recycle_events(status);
CREATE INDEX idx_recycle_event_id ON recycle_events(event_id);

-- ── Fraud Decisions (Agent log) ───────────────────────
CREATE TABLE IF NOT EXISTS fraud_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT REFERENCES recycle_events(event_id),
  phone TEXT,
  decision TEXT NOT NULL,         -- approve | reject | review
  reason TEXT,
  score FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fraud_event ON fraud_decisions(event_id);
CREATE INDEX idx_fraud_phone ON fraud_decisions(phone);

-- ── Vehicle Evaluations ───────────────────────────────
CREATE TABLE IF NOT EXISTS vehicle_evaluations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT UNIQUE NOT NULL,
  phone TEXT,
  patente TEXT,
  marca TEXT,
  modelo TEXT,
  ano INT,
  precio_publicado INT,
  precio_estimado INT,
  decision TEXT,                  -- comprar | negociar | descartar
  sobreprecio_pct FLOAT,
  fraud_score FLOAT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vehicle_phone ON vehicle_evaluations(phone);
CREATE INDEX idx_vehicle_created ON vehicle_evaluations(created_at);

-- ── RLS Policies ──────────────────────────────────────
ALTER TABLE events_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE recycle_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicle_evaluations ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY "service_all_events" ON events_log FOR ALL USING (true);
CREATE POLICY "service_all_wallets" ON wallets FOR ALL USING (true);
CREATE POLICY "service_all_recycle" ON recycle_events FOR ALL USING (true);
CREATE POLICY "service_all_fraud" ON fraud_decisions FOR ALL USING (true);
CREATE POLICY "service_all_vehicle" ON vehicle_evaluations FOR ALL USING (true);

-- Users can only see their own data (via phone)
CREATE POLICY "user_read_own_wallet" ON wallets FOR SELECT USING (phone = current_setting('request.jwt.claims', true)::json->>'phone');
CREATE POLICY "user_read_own_recycle" ON recycle_events FOR SELECT USING (phone = current_setting('request.jwt.claims', true)::json->>'phone');
CREATE POLICY "user_read_own_vehicle" ON vehicle_evaluations FOR SELECT USING (phone = current_setting('request.jwt.claims', true)::json->>'phone');
