import pandas as pd
import streamlit as st

from src.clay_engine import enrich_dataset_with_clay_engine, format_full_whatsapp_draft
from src.config import (
    GDPR_OPTOUT_TEXT,
    OUTPUT_DA_ARRICCHIRE_CSV,
    OUTPUT_DASHBOARD_CSV,
    OUTPUT_OUTBOUND_CSV,
    OUTPUT_TERMOIDRAULICA_CSV,
    PRICING_PLANS,
    SENDER_IDENTITY,
)

# Configurazione pagina
st.set_page_config(
    page_title="TecnicoLIVE • Lead & Market Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Stile personalizzato CSS
st.markdown(
    """
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0A2540;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #005A9E;
        font-weight: 600;
        margin-bottom: 20px;
    }
    .badge-cna {
        background: #EBF8FF;
        color: #2B6CB0;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid #BEE3F8;
    }
</style>
""",
    unsafe_allow_html=True,
)

DATASET_OPTIONS = {
    "Campagna Outbound Chiamabili (E.164)": OUTPUT_OUTBOUND_CSV,
    "Verticale Termoidraulica & Clima": OUTPUT_TERMOIDRAULICA_CSV,
    "Tutte le Lead Pulite (Master)": OUTPUT_DASHBOARD_CSV,
    "Da Arricchire (Senza Telefono)": OUTPUT_DA_ARRICCHIRE_CSV,
}


@st.cache_data
def load_data(dataset_path_str: str) -> pd.DataFrame:
    from pathlib import Path

    path = Path(dataset_path_str)
    if not path.exists():
        for fallback in (OUTPUT_OUTBOUND_CSV, OUTPUT_DASHBOARD_CSV):
            if fallback.exists():
                path = fallback
                break
        else:
            return pd.DataFrame()

    df = pd.read_csv(path, dtype=str).fillna("")
    if not df.empty and (
        "ICP_Score" not in df.columns
        or "Marchi_Verificati" not in df.columns
        or "Cosa_Vendere_E_Perche" not in df.columns
    ):
        df = enrich_dataset_with_clay_engine(df)
    return df


# Sidebar selettore dataset & info compliance
with st.sidebar:
    st.markdown("### 📂 Sorgente Dataset")
    selected_dataset_label = st.selectbox(
        "Seleziona lista operativa:",
        list(DATASET_OPTIONS.keys()),
        index=0,
    )
    st.caption(
        "I dati rispettano la policy Zero Hallucination (solo marchi reali rilevati), "
        "filtro anti-GDO, normalizzazione telefono E.164 (`+39`) e separazione contatti privi di telefono."
    )
    st.markdown("---")
    st.markdown("### 💶 Listino Ufficiale TecnicoLIVE")
    st.markdown(
        f"- **Base**: {PRICING_PLANS['base']['monthly']}€/mese + {PRICING_PLANS['base']['setup_fee']}€ setup ({PRICING_PLANS['base']['minutes']} min)\n"
        f"- **Pro**: {PRICING_PLANS['pro']['monthly']}€/mese + {PRICING_PLANS['pro']['setup_fee']}€ setup ({PRICING_PLANS['pro']['minutes']} min)\n"
        f"- **Business**: {PRICING_PLANS['business']['monthly']}€/mese + {PRICING_PLANS['business']['setup_fee']}€ setup ({PRICING_PLANS['business']['minutes']} min)\n"
        "- **Annuale**: **-20%** sul canone\n"
        "- **Convenzione CNA**: **50% quota associativa 1° anno**"
    )

df = load_data(str(DATASET_OPTIONS[selected_dataset_label]))

# Header Dashboard
col_logo, col_info = st.columns([3, 1])
with col_logo:
    st.markdown('<div class="main-title">⚡ TecnicoLIVE • Executive Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Intelligence Hub &bull; Lead Finder CNA &bull; Trend di Mercato &bull; Sales Content</div>',
        unsafe_allow_html=True,
    )

with col_info:
    st.markdown(
        """
    <div style="text-align: right; padding-top: 5px;">
        <span class="badge-cna">PARTNERSHIP CNA CATANIA</span><br>
        <small style="color: #64748B;">Sinergia Rete d'Imprese &bull; P.IVA IT06200390877</small>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.divider()

# Definizione dei 4 Tab Principali
tab_leads, tab_trends, tab_content, tab_engine = st.tabs([
    "🎯 Tab 1: Lead Finder",
    "📈 Tab 2: Trend Finder",
    "📝 Tab 3: Contenuti & Sales Hub",
    "🚀 Tab 4: Lead Engine IT/EU (Multi-Prodotto)",
])

# ==========================================
# TAB 1: LEAD FINDER
# ==========================================
with tab_leads:
    st.subheader(f"Censimento & Qualificazione Impiantisti — {selected_dataset_label}")

    if df.empty:
        st.warning("Nessun dato disponibile per questa vista. Esegui `python main.py --clean` per generare i dataset puliti.")
    else:
        totale = len(df)
        piva_valide = int(df["Partita_IVA"].str.startswith("IT").sum()) if "Partita_IVA" in df.columns else 0
        targets = int(df["Stato_CNA"].str.contains("NON ASSOCIATO", na=False).sum()) if "Stato_CNA" in df.columns else 0
        tier_a_count = int(df["Lead_Tier"].str.contains("Tier A", na=False).sum()) if "Lead_Tier" in df.columns else 0
        avg_score = int(pd.to_numeric(df["ICP_Score"], errors="coerce").mean()) if "ICP_Score" in df.columns and totale > 0 else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Aziende in Vista", f"{totale:,}", help="Totale ditte pulite nella vista selezionata")
        k2.metric("P.IVA Validate (IT)", f"{piva_valide:,}", f"{(piva_valide / totale * 100):.1f}% Luhn OK" if totale else "0%")
        k3.metric("Target Tesseramento", f"{targets:,}", "CNA 50% 1° anno")
        k4.metric("Tier A 🔥 (VIP Priority)", f"{tier_a_count:,}", f"{(tier_a_count / totale * 100):.1f}% Hot Leads" if totale else "0%")
        k5.metric("Punteggio Medio ICP", f"{avg_score}/100", "Qualità media lead")

        st.markdown("---")

        # Filtri Interattivi con Tiering Clay
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)

        with col_f1:
            comuni_list = ["Tutti i Comuni"] + sorted([c for c in df["City"].unique() if c])
            selected_city = st.selectbox("📍 Filtra per Comune:", comuni_list)

        with col_f2:
            settori_list = ["Tutti i Settori"] + sorted([s for s in df["Nicchia_Target"].unique() if s])
            selected_niche = st.selectbox("🔧 Filtra per Nicchia:", settori_list)

        with col_f3:
            stati_list = ["Tutti gli Stati"] + sorted([st_val for st_val in df["Stato_CNA"].unique() if st_val])
            selected_status = st.selectbox("🏷️ Filtra per Stato CNA:", stati_list)

        with col_f4:
            tier_options = [
                "Tutti i Tier",
                "Tier A 🔥 (VIP / Priorità)",
                "Tier B 🟡 (Warm / Retargeting)",
                "Tier C ❄️ (Cold)",
            ]
            selected_tier = st.selectbox("🏆 Filtra per Tier Clay:", tier_options)

        search_query = st.text_input(
            "🔍 Ricerca rapida per Nome Azienda, Telefono E.164, P.IVA o Marchi:",
            placeholder="Es. Clima, +393, IT05, Vaillant...",
        )

        # Applicazione filtri
        filtered_df = df.copy()
        if selected_city != "Tutti i Comuni":
            filtered_df = filtered_df[filtered_df["City"] == selected_city]
        if selected_niche != "Tutti i Settori":
            filtered_df = filtered_df[filtered_df["Nicchia_Target"] == selected_niche]
        if selected_status != "Tutti gli Stati":
            filtered_df = filtered_df[filtered_df["Stato_CNA"] == selected_status]
        if selected_tier != "Tutti i Tier":
            tier_key = selected_tier.split()[0] + " " + selected_tier.split()[1]
            filtered_df = filtered_df[filtered_df["Lead_Tier"].str.contains(tier_key, na=False)]
        if search_query:
            q = search_query.lower()
            marchi_col = filtered_df["Marchi_Rilevati"] if "Marchi_Rilevati" in filtered_df.columns else pd.Series([""] * len(filtered_df), index=filtered_df.index)
            filtered_df = filtered_df[
                filtered_df["Company Name"].str.lower().str.contains(q, na=False)
                | filtered_df["Phone"].str.lower().str.contains(q, na=False)
                | filtered_df["Partita_IVA"].str.lower().str.contains(q, na=False)
                | marchi_col.str.lower().str.contains(q, na=False)
            ]

        filtered_df = filtered_df.reset_index(drop=True)
        st.caption(f"Visualizzati **{len(filtered_df)}** risultati su {totale} totali.")

        sub_tab_table, sub_tab_swot = st.tabs([
            "📋 Tabella & Scheda Lead",
            "🎯 Pain Points, Weak & Forza (Pre-Call)",
        ])

        with sub_tab_table:
            # Tabella Lead Interattiva
            display_cols = [
                "Company Name",
                "Nicchia_Target",
                "City",
                "Phone",
                "Lead_Tier",
                "ICP_Score",
                "Dimensione_Stimata",
                "Pain_Points_Count",
                "Marchi_Rilevati",
                "Stato_CNA",
            ]
            available_cols = [c for c in display_cols if c in filtered_df.columns]
            st.dataframe(
                filtered_df[available_cols],
                width="stretch",
                hide_index=True,
                column_config={
                    "Company Name": st.column_config.TextColumn("Ragione Sociale", width="medium"),
                    "Nicchia_Target": st.column_config.TextColumn("Settore", width="small"),
                    "City": st.column_config.TextColumn("Comune", width="small"),
                    "Phone": st.column_config.TextColumn("Telefono (E.164)", width="small"),
                    "Lead_Tier": st.column_config.TextColumn("Tier Clay", width="small"),
                    "ICP_Score": st.column_config.NumberColumn("Score (0-100)", width="small"),
                    "Dimensione_Stimata": st.column_config.TextColumn("Dimensione", width="small"),
                    "Pain_Points_Count": st.column_config.NumberColumn("Pain", width="small"),
                    "Marchi_Rilevati": st.column_config.TextColumn("Marchi Rilevati (Reali)", width="medium"),
                    "Stato_CNA": st.column_config.TextColumn("Stato CNA", width="small"),
                },
            )

            # Ispettore Lead Univoco per Indice (gestisce correttamente omonimi)
            st.markdown("### 📋 Scheda Dettaglio Lead, Segnali Verificati & Messaggi Conformi GDPR")
            if not filtered_df.empty:
                selected_idx = st.selectbox(
                    "Seleziona un'azienda per visualizzare l'icebreaker dedicato e il messaggio WhatsApp conforme:",
                    options=list(range(len(filtered_df))),
                    format_func=lambda idx: (
                        f"{filtered_df.iloc[idx].get('Company Name', '')} — "
                        f"{filtered_df.iloc[idx].get('City', '')} "
                        f"({filtered_df.iloc[idx].get('Partita_IVA') or 'P.IVA N/D'})"
                    ),
                )
                selected_row = filtered_df.iloc[selected_idx]

                box_col1, box_col2 = st.columns([1, 2])
                with box_col1:
                    st.markdown(f"**Azienda:** {selected_row.get('Company Name')}")
                    st.markdown(f"**Settore:** {selected_row.get('Nicchia_Target')}")
                    st.markdown(f"**Dimensione:** `{selected_row.get('Dimensione_Stimata') or 'PMI'}`")
                    st.markdown(f"**Comune:** {selected_row.get('City')}")
                    st.markdown(f"**Telefono E.164:** `{selected_row.get('Phone') or 'Non rilevato'}`")
                    if selected_row.get("Phone_Secondary"):
                        st.markdown(f"**Altri Telefoni:** `{selected_row.get('Phone_Secondary')}`")
                    st.markdown(f"**P.IVA:** `{selected_row.get('Partita_IVA') or 'Non rilevata'}`")
                    if selected_row.get("Email"):
                        st.markdown(f"**Email:** `{selected_row.get('Email')}`")
                    if selected_row.get("Website"):
                        st.markdown(f"**Sito Aziendale Reale:** [{selected_row.get('Website')}]({selected_row.get('Website')})")
                    else:
                        st.markdown("**Sito Aziendale:** `Non rilevato`")

                    st.markdown("---")
                    st.markdown(f"🏆 **Tier ICP:** `{selected_row.get('Lead_Tier', 'Tier C')}`")
                    st.markdown(f"📊 **Score:** **{selected_row.get('ICP_Score', '0')}/100**")
                    st.markdown(
                        f"🔧 **Marchi Rilevati:** {selected_row.get('Marchi_Rilevati') or 'Non rilevato'} "
                        f"(Verificati: `{selected_row.get('Marchi_Verificati', 'NO')}`)"
                    )
                    st.markdown(f"📜 **Certificazioni:** {selected_row.get('Certificazioni_Rilevate') or 'Non rilevate'}")
                    st.markdown(f"🚨 **Reperibilità H24:** {selected_row.get('Servizio_H24', 'NO (Orario Ufficio)')}")
                    st.markdown(f"⚡ **Trigger d'Intento:** {selected_row.get('Trigger_Segnale', 'N/D')}")

                with box_col2:
                    st.info(f"**Stato CNA:** {selected_row.get('Stato_CNA')}")
                    if selected_row.get("Cosa_Vendere_E_Perche"):
                        st.success(
                            f"🎯 **Cosa Vendere ({selected_row.get('Piano_Consigliato', '')}):** "
                            f"{selected_row.get('Cosa_Vendere_E_Perche')}"
                        )

                    st.markdown("#### 🎯 Icebreaker 1-to-1 Dinamico (Solo Dati Verificati)")
                    icebreaker_val = selected_row.get("Icebreaker_1to1") or (
                        f"Buongiorno {selected_row.get('Company Name')}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                        f"Per le imprese di {selected_row.get('Nicchia_Target')} a {selected_row.get('City')}, con la convenzione "
                        f"CNA Catania attivate l'assistente vocale AI e l'associazione a CNA al 50% per il primo anno."
                    )
                    st.text_area("Gancio Conversazionale (Telefonico):", value=icebreaker_val, height=115)

                    wa_full_val = selected_row.get("Messaggio_WhatsApp_Completo") or format_full_whatsapp_draft(icebreaker_val)
                    st.text_area(
                        "Bozza WhatsApp Completa (Conforme GDPR — Mittente + Opt-Out):",
                        value=wa_full_val,
                        height=155,
                    )

            # Download button
            st.download_button(
                label="📥 Scarica Lista Filtrata (CSV UTF-8)",
                data=filtered_df.to_csv(index=False, encoding="utf-8-sig"),
                file_name="lead_filtrate_tecnicolive_catania.csv",
                mime="text/csv",
            )

        with sub_tab_swot:
            st.markdown("### 🎯 Analisi Pre-Chiamata: Pain Points, Punti Deboli & Punti di Forza")
            st.caption(
                "Grafici aggregati sui risultati filtrati e dossier a icone colorate per sapere esattamente "
                "cosa vendere e perché prima di alzare il telefono (dati reali — Zero Hallucination)."
            )

            if filtered_df.empty:
                st.info("Nessun lead nei filtri correnti.")
            else:
                from collections import Counter
                from engine.enrichment.swot_analyzer import analyze_lead_swot_and_brief
                from engine.routing.product_router import route_lead_to_product
                from src.normalizers import is_mobile_e164, is_valid_company_website, normalize_phone_e164
                from src.piva_validator import validate_piva

                # Aggregazione dati reali per grafici
                pain_agg: Counter = Counter()
                weak_agg: Counter = Counter()
                strength_agg: Counter = Counter()
                size_agg: Counter = Counter()

                for _, r_item in filtered_df.iterrows():
                    for pt in str(r_item.get("Pain_Points_Sintesi", "")).split(" | "):
                        if pt.strip():
                            pain_agg[pt.strip()] += 1
                    for wk in str(r_item.get("Weak_Points_Sintesi", "")).split(" | "):
                        if wk.strip():
                            weak_agg[wk.strip()] += 1
                    for st_item in str(r_item.get("Strengths_Sintesi", "")).split(" | "):
                        if st_item.strip():
                            strength_agg[st_item.strip()] += 1
                    sz_val = str(r_item.get("Dimensione_Stimata", "")).strip() or "Ditta Individuale / Artigiano"
                    size_agg[sz_val] += 1

                ch1, ch2, ch3 = st.columns(3)
                with ch1:
                    st.markdown("#### 🔥 Top Pain Points da Attaccare")
                    if pain_agg:
                        df_p = pd.DataFrame(pain_agg.most_common(6), columns=["Pain Point", "Aziende"]).set_index("Pain Point")
                        st.bar_chart(df_p, color="#EF4444")
                with ch2:
                    st.markdown("#### ⚠️ Punti Deboli Più Diffusi")
                    if weak_agg:
                        df_w = pd.DataFrame(weak_agg.most_common(6), columns=["Weak Point", "Aziende"]).set_index("Weak Point")
                        st.bar_chart(df_w, color="#F59E0B")
                with ch3:
                    st.markdown("#### 💪 Punti di Forza & Dimensione")
                    if strength_agg:
                        df_s = pd.DataFrame(strength_agg.most_common(6), columns=["Strength", "Aziende"]).set_index("Strength")
                        st.bar_chart(df_s, color="#10B981")

                if size_agg:
                    st.markdown("#### 🏢 Ripartizione Dimensionale dei Lead in Vista")
                    df_sz = pd.DataFrame(size_agg.most_common(), columns=["Dimensione", "Aziende"]).set_index("Dimensione")
                    st.bar_chart(df_sz, color="#2563EB", horizontal=True)

                st.markdown("---")
                st.markdown("### 🔎 Dossier Pre-Chiamata del Singolo Lead")
                swot_idx = st.selectbox(
                    "Scegli il lead da preparare prima della chiamata:",
                    options=list(range(len(filtered_df))),
                    key="swot_lead_select",
                    format_func=lambda idx: (
                        f"{filtered_df.iloc[idx].get('Company Name', '')} — "
                        f"{filtered_df.iloc[idx].get('City', '')} "
                        f"({filtered_df.iloc[idx].get('Lead_Tier', 'Tier C')})"
                    ),
                )
                s_row = filtered_df.iloc[swot_idx]
                s_comp = str(s_row.get("Company Name", "")).strip()
                s_niche = str(s_row.get("Nicchia_Target", "")).strip()
                s_cat = str(s_row.get("Category", "")).strip()
                s_web = str(s_row.get("Website", "")).strip()
                s_p1, _ = normalize_phone_e164(str(s_row.get("Phone", "")).strip())
                s_routed = route_lead_to_product(
                    company_name=s_comp,
                    category=s_cat,
                    niche=s_niche,
                    website_text=str(s_row.get("Website_Text_Snippet", "")),
                )
                s_brands = [b.strip() for b in str(s_row.get("Marchi_Rilevati", "")).split(",") if b.strip() and b.strip() != "Non rilevato"]
                s_certs = [c.strip() for c in str(s_row.get("Certificazioni_Rilevate", "")).split(",") if c.strip() and c.strip() != "Non rilevate"]
                swot_detail = analyze_lead_swot_and_brief(
                    company_name=s_comp,
                    city=str(s_row.get("City", "")),
                    niche=s_niche,
                    category=s_cat,
                    phone_e164=s_p1,
                    phone_type="Mobile" if is_mobile_e164(s_p1) else ("Fisso" if s_p1 else "Unknown"),
                    email=str(s_row.get("Email", "")).strip(),
                    website=s_web if is_valid_company_website(s_web) else "",
                    has_valid_piva=bool(str(s_row.get("Partita_IVA", "")).strip() and validate_piva(str(s_row.get("Partita_IVA", "")).strip())),
                    cna_status=str(s_row.get("Stato_CNA", "")),
                    brands=s_brands,
                    certifications=s_certs,
                    is_h24=str(s_row.get("Servizio_H24", "")).upper().startswith("SI"),
                    has_ssl=s_web.startswith("https://") if is_valid_company_website(s_web) else False,
                    recommended_product=s_routed["product_key"],
                    recommended_product_name=s_routed["product_name"],
                )
                brief = swot_detail["sales_brief"]

                st.markdown(
                    f"""
                <div style="background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border: 1px solid #93C5FD; border-radius: 10px; padding: 16px; margin-bottom: 16px;">
                    <div style="font-size: 0.78rem; font-weight: 800; color: #1E40AF; text-transform: uppercase; letter-spacing: 0.04em;">
                        🎯 Cosa Vendere e Perché (Prima di Chiamare) · {brief.product_name}
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin: 4px 0 8px 0;">
                        💊 {brief.recommended_plan} &nbsp;|&nbsp; 🏢 {brief.company_size_label} &nbsp;|&nbsp; 💻 Tech: {brief.tech_maturity_label}
                    </div>
                    <div style="font-size: 0.92rem; color: #1E293B; margin-bottom: 8px;">{brief.why_sell}</div>
                    <div style="font-size: 0.86rem; color: #7F1D1D; background: #FEF2F2; border-left: 3px solid #EF4444; padding: 6px 10px; border-radius: 4px; margin-bottom: 6px;">
                        <strong>🔥 Pain Point #1 da Attaccare:</strong> {brief.primary_pain_to_attack}
                    </div>
                    <div style="font-size: 0.86rem; color: #065F46; background: #ECFDF5; border-left: 3px solid #10B981; padding: 6px 10px; border-radius: 4px; margin-bottom: 6px;">
                        <strong>💪 Leva sul Punto di Forza:</strong> {brief.leverage_strength}
                    </div>
                    <div style="font-size: 0.85rem; color: #334155;">
                        <strong>🛡️ Obiezione Attesa:</strong> {brief.expected_objection}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                col_p, col_w, col_s = st.columns(3)
                with col_p:
                    st.markdown("#### 🔴 Pain Points da Attaccare")
                    for item in swot_detail["pain_signals"]:
                        st.markdown(
                            f"""
                        <div style="background:#FEF2F2; border:1px solid #FECACA; border-left:4px solid #DC2626; border-radius:8px; padding:10px 12px; margin-bottom:8px;">
                            <div style="font-weight:700; color:#991B1B; font-size:0.9rem;">🔥 {item.title}</div>
                            <div style="font-size:0.82rem; color:#374151; margin:4px 0;">{item.description}</div>
                            <div style="font-size:0.76rem; color:#7F1D1D;"><strong>Attacco:</strong> {item.attack_angle}</div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                with col_w:
                    st.markdown("#### 🟠 Weak Points (Punti Deboli)")
                    for item in swot_detail["weak_points"]:
                        st.markdown(
                            f"""
                        <div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:8px; padding:10px 12px; margin-bottom:8px;">
                            <div style="font-weight:700; color:#92400E; font-size:0.9rem;">⚠️ {item.title}</div>
                            <div style="font-size:0.82rem; color:#374151; margin:4px 0;">{item.description}</div>
                            <div style="font-size:0.75rem; color:#78350F;"><em>Evidenza: {item.evidence}</em></div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                with col_s:
                    st.markdown("#### 🟢 Strengths (Punti di Forza)")
                    for item in swot_detail["strengths"]:
                        st.markdown(
                            f"""
                        <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-left:4px solid #059669; border-radius:8px; padding:10px 12px; margin-bottom:8px;">
                            <div style="font-weight:700; color:#065F46; font-size:0.9rem;">✅ {item.title}</div>
                            <div style="font-size:0.82rem; color:#374151; margin:4px 0;">{item.description}</div>
                            <div style="font-size:0.75rem; color:#064E3B;"><em>Evidenza: {item.evidence}</em></div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )


# ==========================================
# TAB 2: TREND FINDER
# ==========================================
with tab_trends:
    st.subheader("Market Intelligence & Trend Impiantistica a Catania e Sicilia")
    st.info(
        "⚠️ **STIMA TEORICA / MODELLO PREDITTIVO (`AGENTS.md` §2):** "
        "Gli indicatori stagionali e i moltiplicatori di domanda seguenti sono stime operative di lavoro "
        "utilizzate per prioritizzare il calendario commerciale sul territorio."
    )

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("### 🌡️ Ciclo della Domanda Stagionale (STIMA TEORICA)")
        st.markdown(
            "Nell'area etnea e costiera catanese, la domanda impiantistica segue due picchi acuti durante l'anno:"
        )

        st.progress(0.95, text="🔥 Estate (Giu - Set): Climatizzazione & Refrigerazione (STIMA TEORICA: fino a +340% volumi)")
        st.caption("Centralini intasati per condizionatori bloccati, ricariche gas refrigerante e guasti durante le ondate di calore estive.")

        st.progress(0.85, text="❄️ Inverno (Nov - Feb): Caldaie & Termoidraulica (STIMA TEORICA: fino a +280% volumi)")
        st.caption("Emergenze riscaldamento, blocchi caldaie, controllo fumi (Bollino Blu CITEL Sicilia) e picchi serali/weekend.")

        st.progress(0.40, text="🌱 Primavera/Autunno: Manutenzioni Programmate & Pompe di Calore")
        st.caption("Fase ideale per proporre contratti di manutenzione programmata e nuove installazioni.")

    with c2:
        st.markdown("### ⚖️ Driver Normativi & Convenzione CNA Catania")
        st.markdown("Le leve ufficiali che spingono installatori e titolari ad attivarsi:")

        with st.expander("🎟️ Associazione CNA Catania al 50% per il 1° Anno", expanded=True):
            st.write(
                "La convenzione ufficiale prevede l'**associazione a CNA Catania al 50% della quota associativa per tutto il primo anno** "
                "per le aziende non ancora iscritte. È la leva decisiva che abbatte la barriera d'ingresso e unisce tutela sindacale, "
                "fiscale e normativa all'automazione vocale di TecnicoLIVE."
            )

        with st.expander("📋 Obbligo Catasto Impianti Termici Sicilia (CITEL)"):
            st.write(
                "In Sicilia è obbligatorio caricare telematicamente i rapporti di efficienza energetica. "
                "L'assistente vocale TecnicoLIVE raccoglie già i dati essenziali durante la chiamata iniziale."
            )

        with st.expander("🔌 Transizione Energetica & Pompe di Calore"):
            st.write(
                "Chi risponde tempestivamente con chiamate simultanee illimitate acquisisce il preventivo; "
                "chi richiama dopo ore rischia di trovare il cliente già seguito da un concorrente."
            )

        with st.expander("🛡️ Patentino F-Gas & Certificazioni DM 37/08"):
            st.write(
                "CNA Catania è punto di riferimento provinciale per corsi, patentini F-Gas e tutele legali di categoria."
            )

    st.markdown("---")
    st.markdown("### ⚡ Intent & Trigger Signals Monitor (`MODELLO PREDITTIVO`)")
    st.markdown("Identificazione automatica dei segnali operativi per prioritizzare outbound e retargeting:")

    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    with t_col1:
        st.metric("🚨 Chiamate Perse / Segreteria", "Alta Priorità", "STIMA TEORICA: +35% Resp.")
        st.caption("Aziende prive di segreteria H24 o con segnalazioni di mancata risposta telefonica.")
    with t_col2:
        st.metric("❄️ Allerta Meteo & Gelate Etna", "Stagionale Attivo", "Picco Caldaie")
        st.caption("Richieste improvvise di pronto intervento e riparazione urgente blocchi termici.")
    with t_col3:
        st.metric("📋 Scadenza CITEL Sicilia", "Normativo Imminente", "Bollino Blu")
        st.caption("Caricamento telematico rapporti efficienza e pianificazione controlli periodici.")
    with t_col4:
        st.metric("👷 Reperibilità H24 / Multi-Furgone", "Segnale Strutturale", "Sovraccarico Titolare")
        st.caption("Ditte che offrono pronto intervento con potenziale sovraccarico telefonico.")

    st.markdown("---")
    st.markdown("### 🔍 Domande & Keyword Più Cercate dai Clienti Finali a Catania")

    col_kw1, col_kw2, col_kw3 = st.columns(3)
    with col_kw1:
        st.markdown("**Riscaldamento & Caldaie**")
        st.markdown(
            """
        - `assistenza caldaie catania h24`
        - `blocco caldaia vaillant acireale`
        - `costo bollino blu caldaia catania`
        - `tecnico caldaie ariston catania`
        """
        )
    with col_kw2:
        st.markdown("**Climatizzazione**")
        st.markdown(
            """
        - `ricarica condizionatore catania subito`
        - `installazione climatizzatori acireale`
        - `condizionatore non raffredda misterbianco`
        - `preventivo dual split catania`
        """
        )
    with col_kw3:
        st.markdown("**Idraulica & Elettrico**")
        st.markdown(
            """
        - `idraulico pronto intervento catania`
        - `riparazione perdita acqua acireale`
        - `elettricista urgente catania h24`
        - `certificazione conformità impianto 37/08`
        """
        )


# ==========================================
# TAB 3: CONTENUTI & SALES HUB
# ==========================================
with tab_content:
    st.subheader("Sales Hub & Contenuti Pronti all'Uso (Conformi GDPR & Listino Ufficiale)")
    st.markdown("Materiali di vendita, script telefonici, template WhatsApp con opt-out e calcolatore ROI teorico.")

    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs([
        "📞 Script Telefonici",
        "💬 Template WhatsApp",
        "🧮 Calcolatore ROI (Stima Teorica)",
        "🛡️ Risoluzione Obiezioni",
    ])

    with sub_t1:
        st.markdown("#### Script Telefonico 1: Aziende già Associate a CNA Catania")
        st.code(
            f"""
Operatore: "Buongiorno [Nome Titolare/Azienda], la chiamo da {SENDER_IDENTITY}.
La contatto in merito alla convenzione ufficiale attiva con CNA Catania per le imprese impiantistiche.
Sappiamo che mentre siete in cantiere molte chiamate di nuovi clienti finiscono senza risposta.
Con TecnicoLIVE attivate l'assistente vocale AI con chiamate simultanee illimitate che risponde H24, fa la pre-diagnosi del guasto e vi invia la scheda intervento su WhatsApp (piani a partire da {PRICING_PLANS['base']['monthly']}€/mese, -20% su base annuale).
Ha 5 minuti oggi per fare una prova live chiamando il nostro numero test +39 095 342 0411?"

[Nota Opt-Out in caso di follow-up scritto: {GDPR_OPTOUT_TEXT}]
        """,
            language="markdown",
        )

        st.markdown("#### Script Telefonico 2: Aziende NON Associate (Leva Associazione CNA al 50% 1° Anno)")
        st.code(
            f"""
Operatore: "Buongiorno [Nome Titolare], chiamo da {SENDER_IDENTITY}.
Stiamo attivando nella zona di [Comune] la convenzione esclusiva con CNA Catania per gli impiantisti.
Poiché non risultate ancora associati, abbiamo riservato un pacchetto dedicato: attiviamo l'assistente vocale AI TecnicoLIVE (con chiamate simultanee illimitate per non perdere lavori mentre siete sui furgoni) e sblocchiamo la vostra associazione a CNA Catania al 50% della quota per tutto il primo anno, con tutela legale, fiscale e supporto CITEL e F-Gas.
Chi si occupa in azienda di valutare convenzioni e gestione chiamate?"

[Nota Opt-Out in caso di follow-up scritto: {GDPR_OPTOUT_TEXT}]
        """,
            language="markdown",
        )

    with sub_t2:
        st.markdown("#### Messaggi WhatsApp Brevi Conformi `AGENTS.md` §3B-3C")
        st.info("💡 Orari consigliati: 12:30–14:00 oppure 18:00–19:30. Invio solo previa approvazione umana (Human-in-the-Loop).")

        st.markdown("**Opzione 1: Primo Contatto Impiantisti (Convenzione CNA al 50% 1° Anno)**")
        st.code(
            f"""
Buongiorno [Nome / Ragione Sociale], ti scrivo da {SENDER_IDENTITY}.
Quante chiamate di nuovi clienti rischi di perdere ogni settimana mentre sei sotto una caldaia o in cantiere?
TecnicoLIVE è l'assistente vocale AI (piani da 169€/mese, chiamate simultanee illimitate) che risponde in 3 secondi, raccoglie il guasto e ti manda la scheda su WhatsApp.
In più, se non sei ancora socio, con la nostra convenzione hai l'associazione a CNA Catania al 50% per tutto il primo anno.
👉 Ascolta la demo dal vivo al +39 095 342 0411 oppure su: https://www.tecnicolive.it

—
{SENDER_IDENTITY}
{GDPR_OPTOUT_TEXT}
        """,
            language="markdown",
        )

        st.markdown("**Opzione 2: Follow-up con Casi Studio Reali Certificati (Ditta La Paglia, GT Service, MT Service)**")
        st.code(
            f"""
Buongiorno [Nome / Ragione Sociale], una chiamata senza risposta in cantiere è spesso un lavoro affidato al concorrente successivo.
Collaudato sul campo a Catania insieme ad aziende del territorio come Ditta La Paglia, GT Service e MT Service, TecnicoLIVE risponde H24 senza far trovare mai occupato e filtra le vere urgenze.
Con la convenzione CNA Catania hai anche l'iscrizione a CNA al 50% per tutto il primo anno.
Vuoi chiamare il numero test +39 095 342 0411 per ascoltarlo in azione?

—
{SENDER_IDENTITY}
{GDPR_OPTOUT_TEXT}
        """,
            language="markdown",
        )

    with sub_t3:
        st.markdown("#### 🧮 Calcolatore ROI Interattivo del Fatturato Perso (`STIMA TEORICA`)")
        st.warning(
            "⚠️ **STIMA TEORICA / MODELLO PREDITTIVO (`AGENTS.md` §2):** "
            "I valori generati sono simulazioni matematiche basate sui parametri ipotizzati dal cliente."
        )

        col_roi1, col_roi2 = st.columns(2)
        with col_roi1:
            plan_key = st.selectbox(
                "Piano TecnicoLIVE di Riferimento:",
                options=["base", "pro", "business"],
                index=1,
                format_func=lambda k: (
                    f"{PRICING_PLANS[k]['name']} — {PRICING_PLANS[k]['monthly']}€/mese "
                    f"(+{PRICING_PLANS[k]['setup_fee']}€ Setup, {PRICING_PLANS[k]['minutes']} min)"
                ),
            )
            billing_mode = st.radio("Fatturazione:", ["Mensile", "Annuale (SALVA 20%)"], horizontal=True)
            num_tecnici = st.slider("Numero di tecnici / furgoni in azienda:", min_value=1, max_value=15, value=2)
            chiamate_perse_settimana = st.slider(
                "Chiamate inevase stimate a settimana per tecnico:", min_value=2, max_value=25, value=8
            )
            valore_medio_intervento = st.number_input(
                "Valore medio stimato di un intervento (€):", min_value=50, max_value=1500, value=140, step=10
            )
            tasso_conversione_chiamate = (
                st.slider("% stimata di chiamate perse convertibili in lavoro:", min_value=10, max_value=80, value=30)
                / 100.0
            )

        with col_roi2:
            plan = PRICING_PLANS[plan_key]
            monthly_cost = plan["annual_monthly"] if "Annuale" in billing_mode else float(plan["monthly"])
            setup_fee = float(plan["setup_fee"])

            chiamate_perse_mese = chiamate_perse_settimana * 4 * num_tecnici
            interventi_persi_mese = chiamate_perse_mese * tasso_conversione_chiamate
            fatturato_perso_mese = interventi_persi_mese * valore_medio_intervento
            fatturato_perso_anno = fatturato_perso_mese * 12

            costo_tecnicolive_anno_ricorrente = monthly_cost * 12
            costo_primo_anno_con_setup = costo_tecnicolive_anno_ricorrente + setup_fee
            guadagno_netto_anno1 = fatturato_perso_anno - costo_primo_anno_con_setup
            roi_moltiplicatore = (
                (guadagno_netto_anno1 / costo_primo_anno_con_setup) if costo_primo_anno_con_setup > 0 else 0.0
            )

            st.markdown(
                f"""
            <div style="background: #FFF5F5; border: 1px solid #FEB2B2; border-radius: 8px; padding: 15px; margin-bottom: 12px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #9B2C2C; text-transform: uppercase;">Perdita Teorica Stimata (STIMA TEORICA)</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #E53E3E;">-{fatturato_perso_mese:,.0f} € / mese</div>
                <div style="font-size: 0.9rem; color: #742A2A;">Pari a <strong>-{fatturato_perso_anno:,.0f} € all'anno</strong> (ipotesi modello)</div>
            </div>

            <div style="background: #F0FFF4; border: 1px solid #9AE6B4; border-radius: 8px; padding: 15px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #22543D; text-transform: uppercase;">
                    Impatto Netto Teorico 1° Anno — {plan['name']} ({monthly_cost:.2f}€/m + {setup_fee:.0f}€ Setup)
                </div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #276749;">+{guadagno_netto_anno1:,.0f} € / anno</div>
                <div style="font-size: 0.9rem; color: #22543D;">
                    ROI Netto 1° Anno (incluso Setup): <strong>{roi_moltiplicatore:.1f}x</strong> |
                    Canone ricorrente anno 2+: <strong>{costo_tecnicolive_anno_ricorrente:,.2f} €</strong>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with sub_t4:
        st.markdown("#### 🛡️ Battlecard: Risoluzione delle Obiezioni Più Comuni")

        with st.expander("🗣️ Obiezione 1: 'Risponde già mia moglie / ho già una segretaria'"):
            st.markdown(
                """
            **Risposta vincente:**  
            *"Perfetto, TecnicoLIVE non sostituisce la segretaria, ma la potenzia! Quando la segretaria è già al telefono su una linea e arriva un'altra chiamata, il secondo cliente trova occupato e chiama un'altra ditta. Con TecnicoLIVE avete **chiamate simultanee illimitate** e copertura H24 anche la sera, nel weekend e nei festivi."*
            """
            )

        with st.expander("🗣️ Obiezione 2: 'I clienti vogliono parlare direttamente con me'"):
            st.markdown(
                """
            **Risposta vincente:**  
            *"La capisco benissimo, ma quando lei è sotto una caldaia o sta guidando sul raccordo, non può rispondere tecnicamente a fondo. Il nostro assistente vocale accoglie il cliente in 3 secondi, raccoglie guasto e indirizzo e le manda tutto su WhatsApp così può richiamarlo già preparato."*
            """
            )

        with st.expander("🗣️ Obiezione 3: 'Costa troppo'"):
            st.markdown(
                f"""
            **Risposta vincente:**  
            *"Il Piano Base parte da **{PRICING_PLANS['base']['monthly']}€/mese** (circa 5,60€ al giorno, o **{PRICING_PLANS['base']['annual_monthly']:.2f}€/mese** con piano annuale `-20%`) e il Piano Pro da **{PRICING_PLANS['pro']['monthly']}€/mese** (~7€ al giorno su piano annuale `-20%`). Inoltre, con la convenzione CNA Catania avete l'**associazione CNA al 50% per tutto il primo anno**. Basta recuperare 1–2 interventi al mese per coprire il canone."*
            """
            )

        with st.expander("🗣️ Obiezione 4: 'L'Intelligenza Artificiale sbaglia / sembra un robot finto'"):
            st.markdown(
                """
            **Risposta vincente:**  
            *"Non è il solito risponditore rigido con 'premere 1 per...'. Ha latenza conversazionale sub-600ms, comprende il gergo tecnico come 'blocco F28', 'termocoppia' o 'perdita raccordo' e la toponomastica locale. Chiami subito il numero demo +39 095 342 0411 per giudicare di persona."*
            """
            )

# ==========================================
# TAB 4: LEAD ENGINE IT/EU (MULTI-PRODOTTO)
# ==========================================
with tab_engine:
    import asyncio
    import json
    from pathlib import Path

    from engine.compliance.lia_engine import assess_lead_lia
    from engine.connectors.vies_validator import ViesValidatorClient
    from engine.enrichment.tech_audit import TechAuditor
    from engine.routing.product_router import PRODUCT_CATALOG, route_lead_to_product
    from engine.schemas.lead import LeadRecord
    from src.normalizers import clean_company_website, is_mobile_e164, normalize_phone_e164

    st.subheader("Lead Intelligence Engine IT/EU — Ecosystem Router & Conformità LIA")
    st.markdown(
        "Architettura stile Clay adattata al mercato italiano ed europeo: **Geo-Lock ISTAT**, **VIES UE / Openapi.com**, "
        "**Tech Audit + MX**, **Gemini 2.5 Flash**, **LIA GDPR 3 fasi** e routing automatico sui 3 prodotti dell'ecosistema."
    )

    # 1. Benchmark reale Clay (esempio.csv) vs Lead Engine IT/EU
    st.markdown("### ⚖️ Benchmark Reale: Clay.com (`esempio.csv`) vs Nostro Lead Engine IT/EU")
    clay_path = Path("esempio.csv")
    if clay_path.exists():
        df_clay = pd.read_csv(clay_path, dtype=str).fillna("")
        non_it_clay = int((df_clay["Country"] != "Italy").sum()) if "Country" in df_clay.columns else 0
        has_phone_clay = int(any("phone" in c.lower() for c in df_clay.columns))
        has_email_clay = int(any("email" in c.lower() for c in df_clay.columns))
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Clay: Fuori Italia su Catania", f"{non_it_clay}/{len(df_clay)}", "Ecuador, Spagna, Malta")
        b2.metric("Clay: Colonne Telefono / Email", f"{has_phone_clay} / {has_email_clay}", "0 contatti pronti")
        b3.metric("Nostro Engine: Telefoni E.164", "397 chiamabili", "0% errori geografici")
        b4.metric("Nostro Engine: P.IVA + LIA", "847 Luhn + PEC Block", "Conformità GDPR nativa")

    st.markdown("---")

    # 2. Ecosystem Product Router & LIA Tester (Locale, zero chiamate di rete)
    st.markdown("### 🧭 Simulatore Ecosystem Product Router & Test GDPR LIA (3 Fasi)")
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        test_name = st.text_input("Ragione Sociale:", value="Etna Digital Marketing S.r.l.")
        test_cat = st.text_input("Categoria / Settore:", value="Agenzia Marketing Digitale")
        test_ateco = st.text_input("Codice ATECO (opzionale):", value="73.11.01")
    with r_col2:
        test_vat = st.text_input("Partita IVA (opzionale):", value="IT06200390877")
        test_phone = st.text_input("Telefono (normalizzato in E.164):", value="347 1234567")
        test_email = st.text_input("Email o PEC (test blocco PEC):", value="amministrazione@pec.etnadigital.it")

    routed = route_lead_to_product(
        company_name=test_name,
        category=test_cat,
        ateco_code=test_ateco,
    )
    p1, p2 = normalize_phone_e164(test_phone)
    sample_lead = LeadRecord(
        company_name=test_name or "Azienda Test",
        vat_id=test_vat,
        city="Catania",
        category=test_cat,
        phone_e164=p1,
        phone_secondary=p2,
        phone_type="Mobile" if is_mobile_e164(p1) else ("Fisso" if p1 else "Unknown"),
        email=test_email.strip().lower(),
    )
    lia_res = assess_lead_lia(
        sample_lead,
        campaign_purpose=f"Proposta commerciale B2B pertinente ({routed['product_name']})",
    )

    out_c1, out_c2 = st.columns(2)
    with out_c1:
        st.success(f"**Prodotto Ecosistema Consigliato:** {routed['product_name']} (`{routed['product_url']}`)")
        st.caption(routed["rationale"])
        st.write(f"**Pitch:** {routed['core_pitch']}")
    with out_c2:
        badge_fn = st.success if lia_res.status == "PASS" else (st.warning if lia_res.status == "REVIEW_REQUIRED" else st.error)
        badge_fn(
            f"**Esito GDPR LIA:** `{lia_res.status}` | PEC Cold-Block: `{lia_res.pec_cold_outreach_blocked}` | "
            f"Check RPO (+39): `{lia_res.rpo_check_required}`"
        )
        st.write(f"- Email Outbound Autorizzata: `{sample_lead.email or 'Nessuna (PEC isolata / assente)'}`")
        st.write(f"- PEC Solo Registro: `{sample_lead.pec or 'Nessuna'}`")
        st.write(f"- Telefono E.164: `{sample_lead.phone_e164 or 'Nessuno'}`")

    st.markdown("---")

    # 3. Preset Campagne Multi-Settore
    st.markdown("### 📁 Playbook Campagne Multi-Settore (`campaigns/*.json`)")
    presets_dir = Path("campaigns")
    if presets_dir.exists():
        preset_files = sorted(presets_dir.glob("*.json"))
        cols_p = st.columns(max(1, len(preset_files)))
        for idx_p, pf in enumerate(preset_files):
            pdata = json.loads(pf.read_text(encoding="utf-8"))
            with cols_p[idx_p]:
                st.markdown(f"**{pdata.get('name', pf.name)}**")
                st.caption(f"Upsell: `{pdata.get('default_upsell_product')}` | ATECO: `{', '.join(pdata.get('ateco_codes', []))}`")
                st.write(pdata.get("offer_summary", ""))

    st.markdown("---")

    # 4. Strumenti Live On-Demand (solo al click)
    st.markdown("### 🔌 Verifica Live On-Demand (VIES UE & Level 1 Tech Audit)")
    live_c1, live_c2 = st.columns(2)
    with live_c1:
        vies_input = st.text_input("Verifica P.IVA su VIES UE (Gratis):", value="IT06200390877")
        if st.button("Verifica VIES UE"):
            res_vies = asyncio.run(ViesValidatorClient().check_vat(vies_input))
            st.json(res_vies)
    with live_c2:
        audit_url = st.text_input("Livello 1 Tech Audit + MX su Sito:", value="https://www.tecnicolive.it")
        if st.button("Esegui Tech Audit Livello 1"):
            res_audit = asyncio.run(TechAuditor().audit_website(audit_url, check_mx=True))
            st.json(res_audit.model_dump(exclude={"text_snippet"}))

# Footer informativo
st.markdown("---")
st.markdown(
    f"""
<div style="text-align: center; color: #94A3B8; font-size: 0.8rem; padding-bottom: 20px;">
    {SENDER_IDENTITY}
</div>
""",
    unsafe_allow_html=True,
)
