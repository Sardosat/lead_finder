-- Migration 002: Isolated LeadFinder 876 tables in existing Supabase PostgreSQL (rsksystem)
-- All tables are strictly prefixed with lf876_ to avoid any collision with existing tables.

CREATE TABLE IF NOT EXISTS lf876_searches (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  vertical TEXT NOT NULL DEFAULT '',
  product_target TEXT NOT NULL DEFAULT 'TecnicoLIVE',
  status TEXT NOT NULL DEFAULT 'Bozza',
  geo_scope TEXT NOT NULL DEFAULT '',
  geo_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  ateco_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
  keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  prefilters JSONB NOT NULL DEFAULT '{}'::jsonb,
  enrichment_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  budget_cap_eur NUMERIC(10, 2) NOT NULL DEFAULT 5.00,
  estimated_cost_eur NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
  actual_cost_eur NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
  discovery_source TEXT NOT NULL DEFAULT 'archivio_locale',
  match_count INTEGER NOT NULL DEFAULT 0,
  created_by TEXT NOT NULL DEFAULT 'admin',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lf876_leads (
  id TEXT PRIMARY KEY,
  search_id TEXT REFERENCES lf876_searches(id) ON DELETE CASCADE,
  company_name TEXT NOT NULL,
  city TEXT DEFAULT '',
  province TEXT DEFAULT '',
  region TEXT DEFAULT '',
  address TEXT DEFAULT '',
  phone TEXT DEFAULT '',
  email TEXT DEFAULT '',
  pec_email TEXT DEFAULT '',
  website TEXT DEFAULT '',
  piva TEXT DEFAULT '',
  piva_luhn_valid BOOLEAN NOT NULL DEFAULT FALSE,
  ateco_code TEXT DEFAULT '',
  niche TEXT DEFAULT '',
  product_fit TEXT DEFAULT 'TecnicoLIVE',
  tier TEXT DEFAULT 'C',
  icp_score INTEGER NOT NULL DEFAULT 0,
  lia_status TEXT DEFAULT 'REVIEW_REQUIRED',
  google_place_id TEXT DEFAULT '',
  google_rating NUMERIC(3, 2),
  google_reviews_count INTEGER,
  negative_review_quotes JSONB NOT NULL DEFAULT '[]'::jsonb,
  intent_signal TEXT DEFAULT '',
  tech_audit JSONB NOT NULL DEFAULT '{}'::jsonb,
  conversion_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
  pixels_detected JSONB NOT NULL DEFAULT '[]'::jsonb,
  social_links JSONB NOT NULL DEFAULT '{}'::jsonb,
  decision_makers JSONB NOT NULL DEFAULT '[]'::jsonb,
  brands_found JSONB NOT NULL DEFAULT '[]'::jsonb,
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lf876_leads_search_id ON lf876_leads(search_id);
CREATE INDEX IF NOT EXISTS idx_lf876_leads_place_id ON lf876_leads(google_place_id);
CREATE INDEX IF NOT EXISTS idx_lf876_leads_tier ON lf876_leads(tier);

CREATE TABLE IF NOT EXISTS lf876_exports (
  id TEXT PRIMARY KEY,
  search_id TEXT NOT NULL DEFAULT '',
  search_name TEXT NOT NULL DEFAULT '',
  format TEXT NOT NULL DEFAULT 'CSV_SEMI',
  filename TEXT NOT NULL DEFAULT '',
  row_count INTEGER NOT NULL DEFAULT 0,
  hitl_approved BOOLEAN NOT NULL DEFAULT FALSE,
  content_preview TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lf876_suppressions (
  suppression_key TEXT PRIMARY KEY,
  company_name TEXT DEFAULT '',
  reason TEXT DEFAULT 'OPT_OUT_RICHIESTA',
  created_by TEXT DEFAULT 'admin',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lf876_outreach_approvals (
  id SERIAL PRIMARY KEY,
  search_id TEXT NOT NULL,
  lead_key TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'EMAIL',
  approved BOOLEAN NOT NULL DEFAULT FALSE,
  approved_by TEXT DEFAULT 'admin',
  notes TEXT DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(search_id, lead_key, channel)
);
