-- Supabase / PostgreSQL Schema (EU Region) — Lead Intelligence Engine IT/EU
-- Multi-tenant architecture with Row Level Security (RLS), credit ledger & GDPR LIA audit trail.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. WORKSPACES (Multi-tenant organizations / clients)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_user_id UUID NOT NULL,
    vat_id TEXT DEFAULT '',
    country_code CHAR(2) NOT NULL DEFAULT 'IT',
    default_product TEXT NOT NULL DEFAULT 'rsksystem'
        CHECK (default_product IN ('monetizelab', 'rsksystem', 'tecnicolive')),
    credits_balance NUMERIC(12, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. CAMPAIGNS
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_slug TEXT NOT NULL,
    name TEXT NOT NULL,
    target_vertical TEXT NOT NULL,
    ateco_codes TEXT[] NOT NULL DEFAULT '{}',
    nace_codes TEXT[] NOT NULL DEFAULT '{}',
    search_queries TEXT[] NOT NULL DEFAULT '{}',
    geo_filter JSONB NOT NULL DEFAULT '{}'::jsonb,
    default_upsell_product TEXT CHECK (default_upsell_product IN ('monetizelab', 'rsksystem', 'tecnicolive')),
    offer_summary TEXT NOT NULL,
    enrichment_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'completed', 'paused')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, campaign_slug)
);

-- 3. LEADS (Canonical Italian/European SMB Schema)
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    company_name TEXT NOT NULL,
    vat_id TEXT DEFAULT '',
    tax_code TEXT DEFAULT '',
    country_code CHAR(2) NOT NULL DEFAULT 'IT',
    region TEXT DEFAULT '',
    province CHAR(2) DEFAULT '',
    city TEXT DEFAULT '',
    istat_code TEXT DEFAULT '',
    postal_code TEXT DEFAULT '',
    address TEXT DEFAULT '',
    phone_e164 TEXT DEFAULT '',
    phone_secondary TEXT DEFAULT '',
    phone_type TEXT DEFAULT 'Unknown' CHECK (phone_type IN ('Mobile', 'Fisso', 'Unknown')),
    email TEXT DEFAULT '',
    email_mx_valid BOOLEAN,
    pec_registry_only TEXT DEFAULT '',
    website TEXT DEFAULT '',
    source TEXT NOT NULL DEFAULT 'places',
    google_place_id TEXT DEFAULT '',
    category TEXT DEFAULT '',
    niche TEXT DEFAULT '',
    tech_audit JSONB NOT NULL DEFAULT '{}'::jsonb,
    registry_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    ai_qualification JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommended_product TEXT NOT NULL DEFAULT 'rsksystem'
        CHECK (recommended_product IN ('monetizelab', 'rsksystem', 'tecnicolive')),
    icp_fit_score SMALLINT NOT NULL DEFAULT 0 CHECK (icp_fit_score BETWEEN 0 AND 100),
    lead_tier TEXT NOT NULL DEFAULT 'Tier C',
    lia_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
        CHECK (lia_status IN ('PASS', 'REVIEW_REQUIRED', 'BLOCKED')),
    rpo_check_required BOOLEAN NOT NULL DEFAULT FALSE,
    enrichment_cost_eur NUMERIC(10, 4) NOT NULL DEFAULT 0,
    human_approved_for_export BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_ws_vat ON leads(workspace_id, vat_id) WHERE vat_id <> '';
CREATE INDEX IF NOT EXISTS idx_leads_ws_phone ON leads(workspace_id, phone_e164) WHERE phone_e164 <> '';
CREATE INDEX IF NOT EXISTS idx_leads_ws_istat ON leads(workspace_id, istat_code);
CREATE INDEX IF NOT EXISTS idx_leads_ws_product_tier ON leads(workspace_id, recommended_product, lead_tier);

-- 4. ENRICHMENT JOBS
CREATE TABLE IF NOT EXISTS enrichment_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    stage TEXT NOT NULL DEFAULT 'raw'
        CHECK (stage IN ('raw', 'deduped', 'l1_crawled', 'l2_ai_qualified', 'l3_registry', 'lia_verified', 'failed')),
    total_leads INTEGER NOT NULL DEFAULT 0,
    processed_leads INTEGER NOT NULL DEFAULT 0,
    total_cost_eur NUMERIC(10, 4) NOT NULL DEFAULT 0,
    error_message TEXT DEFAULT '',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

-- 5. CREDITS LEDGER
CREATE TABLE IF NOT EXISTS credits_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    delta_eur NUMERIC(10, 4) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. SUPPRESSION LIST (Global & per-workspace GDPR opt-out)
CREATE TABLE IF NOT EXISTS suppression_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    phone_e164 TEXT DEFAULT '',
    email TEXT DEFAULT '',
    vat_id TEXT DEFAULT '',
    reason TEXT NOT NULL DEFAULT 'CANCELLAMI',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suppression_lookup
    ON suppression_list(phone_e164, email, vat_id);

-- 7. LIA AUDIT RECORDS (3-stage GDPR Accountability Trail)
CREATE TABLE IF NOT EXISTS lia_audit_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    legal_basis TEXT NOT NULL DEFAULT 'Art. 6(1)(f) GDPR',
    purpose_test JSONB NOT NULL,
    necessity_test JSONB NOT NULL,
    balancing_test JSONB NOT NULL,
    pec_cold_outreach_blocked BOOLEAN NOT NULL DEFAULT TRUE,
    rpo_check_required BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'REVIEW_REQUIRED', 'BLOCKED')),
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ROW LEVEL SECURITY (Multi-Tenant Isolation)
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrichment_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppression_list ENABLE ROW LEVEL SECURITY;
ALTER TABLE lia_audit_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspace_owner_policy ON workspaces
    USING (owner_user_id = auth.uid());

CREATE POLICY campaigns_ws_policy ON campaigns
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_user_id = auth.uid()));

CREATE POLICY leads_ws_policy ON leads
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_user_id = auth.uid()));

CREATE POLICY jobs_ws_policy ON enrichment_jobs
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_user_id = auth.uid()));

CREATE POLICY ledger_ws_policy ON credits_ledger
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_user_id = auth.uid()));

CREATE POLICY suppression_ws_policy ON suppression_list
    USING (workspace_id IS NULL OR workspace_id IN (SELECT id FROM workspaces WHERE owner_user_id = auth.uid()));

CREATE POLICY lia_ws_policy ON lia_audit_records
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_user_id = auth.uid()));
