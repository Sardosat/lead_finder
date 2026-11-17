import streamlit as st
import pandas as pd
from pathlib import Path

# Configurazione pagina
st.set_page_config(
    page_title="TecnicoLIVE • Lead & Market Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = Path("data")
FILE_ALL_LEADS = DATA_DIR / "tutte_le_lead.csv"
FILE_TARGETS = DATA_DIR / "target_tesseramento_cna.csv"
FILE_ASSOCIATI = DATA_DIR / "associati_rilevati.csv"
FILE_OUTBOUND = DATA_DIR / "campagna_outbound_tecnicolive.csv"

# Stile personalizzato CSS
st.markdown("""
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
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #1A365D;
    }
    .metric-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        font-weight: 700;
        color: #64748B;
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
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    if FILE_OUTBOUND.exists():
        df = pd.read_csv(FILE_OUTBOUND, dtype=str).fillna("")
    elif FILE_ALL_LEADS.exists():
        df = pd.read_csv(FILE_ALL_LEADS, dtype=str).fillna("")
    else:
        df = pd.DataFrame()
    return df


df = load_data()

# Header Dashboard
col_logo, col_info = st.columns([3, 1])
with col_logo:
    st.markdown('<div class="main-title">⚡ TecnicoLIVE • Executive Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Intelligence Hub &bull; Lead Finder CNA &bull; Trend di Mercato &bull; Sales Content</div>', unsafe_allow_html=True)

with col_info:
    st.markdown("""
    <div style="text-align: right; padding-top: 5px;">
        <span class="badge-cna">PARTNERSHIP CNA CATANIA</span><br>
        <small style="color: #64748B;">Piazza dei Martiri 8, Catania</small>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Definizione dei 3 Tab Principali
tab_leads, tab_trends, tab_content = st.tabs([
    "🎯 Tab 1: Lead Finder",
    "📈 Tab 2: Trend Finder",
    "📝 Tab 3: Contenuti & Sales Hub"
])

# ==========================================
# TAB 1: LEAD FINDER
# ==========================================
with tab_leads:
    st.subheader("Censimento & Qualificazione Impiantisti (Catania e Provincia)")

    if df.empty:
        st.warning("Nessun dato trovato nella cartella data/. Esegui prima `python main.py` per generare le lead.")
    else:
        # Metriche in evidenza
        totale = len(df)
        piva_valide = len(df[df["Partita_IVA"].str.startswith("IT")])
        associati = len(df[df["Stato_CNA"].str.contains("ASSOCIATO RILEVATO", na=False)])
        targets = len(df[df["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)])

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Aziende Censite", f"{totale:,}", help="Totale ditte qualificate su Catania e provincia")
        k2.metric("P.IVA Validate (IT)", f"{piva_valide:,}", f"{(piva_valide/totale*100):.1f}% con codice Luhn", delta_color="normal")
        k3.metric("Soci CNA Rilevati", f"{associati}", "Convenzione diretta attiva")
        k4.metric("Target Tesseramento", f"{targets:,}", "Pronti per offerta combinata")

        st.markdown("---")

        # Filtri Interattivi
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            comuni_list = ["Tutti i Comuni"] + sorted([c for c in df["City"].unique() if c])
            selected_city = st.selectbox("📍 Filtra per Comune:", comuni_list)

        with col_f2:
            settori_list = ["Tutti i Settori"] + sorted([s for s in df["Nicchia_Target"].unique() if s])
            selected_niche = st.selectbox("🔧 Filtra per Nicchia:", settori_list)

        with col_f3:
            stati_list = ["Tutti gli Stati"] + sorted([st_val for st_val in df["Stato_CNA"].unique() if st_val])
            selected_status = st.selectbox("🏷️ Filtra per Stato CNA:", stati_list)

        search_query = st.text_input("🔍 Ricerca rapida per Nome Azienda, Telefono o Partita IVA:", placeholder="Es. Clima, 095, IT05...")

        # Applicazione filtri
        filtered_df = df.copy()
        if selected_city != "Tutti i Comuni":
            filtered_df = filtered_df[filtered_df["City"] == selected_city]
        if selected_niche != "Tutti i Settori":
            filtered_df = filtered_df[filtered_df["Nicchia_Target"] == selected_niche]
        if selected_status != "Tutti gli Stati":
            filtered_df = filtered_df[filtered_df["Stato_CNA"] == selected_status]
        if search_query:
            q = search_query.lower()
            filtered_df = filtered_df[
                filtered_df["Company Name"].str.lower().str.contains(q, na=False) |
                filtered_df["Phone"].str.lower().str.contains(q, na=False) |
                filtered_df["Partita_IVA"].str.lower().str.contains(q, na=False)
            ]

        st.caption(f"Visualizzati **{len(filtered_df)}** risultati su {totale} totali.")

        # Tabella Lead Interattiva
        display_cols = ["Company Name", "Nicchia_Target", "City", "Phone", "Partita_IVA", "Stato_CNA"]
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Company Name": st.column_config.TextColumn("Ragione Sociale", width="large"),
                "Nicchia_Target": st.column_config.TextColumn("Settore", width="medium"),
                "City": st.column_config.TextColumn("Comune", width="small"),
                "Phone": st.column_config.TextColumn("Telefono", width="medium"),
                "Partita_IVA": st.column_config.TextColumn("Partita IVA (IT)", width="small"),
                "Stato_CNA": st.column_config.TextColumn("Stato Affiliazione", width="medium"),
            }
        )

        # Ispettore Lead e Pitch di Vendita
        st.markdown("### 📋 Scheda Dettaglio Lead & Pitch Commerciale")
        if not filtered_df.empty:
            lead_names = filtered_df["Company Name"].tolist()
            selected_lead_name = st.selectbox("Seleziona un'azienda per visualizzare il pitch dedicato:", lead_names)
            selected_row = filtered_df[filtered_df["Company Name"] == selected_lead_name].iloc[0]

            box_col1, box_col2 = st.columns([1, 2])
            with box_col1:
                st.markdown(f"**Azienda:** {selected_row.get('Company Name')}")
                st.markdown(f"**Settore:** {selected_row.get('Nicchia_Target')}")
                st.markdown(f"**Comune:** {selected_row.get('City')}")
                st.markdown(f"**Telefono:** `{selected_row.get('Phone')}`")
                st.markdown(f"**P.IVA:** `{selected_row.get('Partita_IVA') or 'Non rilevata'}`")
                if selected_row.get("Website"):
                    st.markdown(f"**Sito:** [{selected_row.get('Website')}]({selected_row.get('Website')})")

            with box_col2:
                st.info(f"**Stato CNA:** {selected_row.get('Stato_CNA')}")
                st.markdown("**🎯 Script Telefonico Personalizzato per Chiamata / WhatsApp:**")
                pitch_text = selected_row.get("Pitch_Commerciale_TecnicoLIVE") or (
                    f"Buongiorno {selected_row.get('Company Name')}, vi contattiamo da TecnicoLIVE. "
                    f"In qualità di azienda di {selected_row.get('Nicchia_Target')} a {selected_row.get('City')}, "
                    f"stiamo attivando la convenzione con CNA Catania per non perdere chiamate in cantiere e tesserarvi a condizioni agevolate."
                )
                st.text_area("Copia il testo:", value=pitch_text, height=100)

        # Download button
        st.download_button(
            label="📥 Scarica Lista Filtrata in CSV (UTF-8)",
            data=filtered_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="lead_filtrate_catania.csv",
            mime="text/csv"
        )


# ==========================================
# TAB 2: TREND FINDER
# ==========================================
with tab_trends:
    st.subheader("Market Intelligence & Trend Impiantistica a Catania e Sicilia")
    st.markdown("Monitoraggio in tempo reale dei cicli stagionali, delle normative e della domanda di pronto intervento.")

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("### 🌡️ Ciclo della Domanda Stagionale (Catania & Provincia)")
        st.markdown("""
        Nell'area etnea e costiera catanese, la domanda impiantistica segue due picchi acuti durante l'anno:
        """)

        st.progress(0.95, text="🔥 Estate (Giu - Set): Climatizzazione & Refrigerazione (+340% chiamate)")
        st.caption("Centralini intasati per condizionatori bloccati, ricariche gas refrigerante e guasti improvvisi durante ondate di calore a 40°C+. Gli artigiani perdono fino al 60% delle chiamate.")

        st.progress(0.85, text="❄️ Inverno (Nov - Feb): Caldaie & Termoidraulica (+280% chiamate)")
        st.caption("Emergenze riscaldamento, blocchi caldaie, controllo fumi (Bollino Blu CITEL Sicilia) e manutenzioni straordinarie. Picco di chiamate serali e nel weekend.")

        st.progress(0.40, text="🌱 Primavera/Autunno: Transizione Energetica & Pompe di Calore")
        st.caption("Fase ideale per proporre contratti di manutenzione programmata e installazioni di pompe di calore e fotovoltaico.")

    with c2:
        st.markdown("### ⚖️ Driver Normativi & Incentivi Chiave (2026)")
        st.markdown("""
        I temi normativi che spingono installatori e titolari ad automatizzarsi e associarsi a CNA:
        """)

        with st.expander("📋 Obbligo Catasto Impianti Termici Sicilia (CITEL)", expanded=True):
            st.write("In Sicilia è obbligatorio caricare telematicamente i rapporti di efficienza energetica. I tecnici lamentano ore perse la sera dopo il cantiere; l'assistente vocale TecnicoLIVE automatizza la raccolta dati durante la chiamata.")

        with st.expander("🔌 Transizione 5.0 & Pompe di Calore"):
            st.write("La transizione verso sistemi ibridi e pompe di calore richiede più preventivi e consulenza tecnica telefonica. Chi risponde entro 3 squilli acquisisce il cliente; chi richiama dopo 2 ore trova il lavoro già assegnato.")

        with st.expander("🛡️ Patentino F-Gas & Certificazioni FGAS"):
            st.write("CNA Catania è punto di riferimento provinciale per corsi, patentini e tutele legali. Ottima leva di conversione per le aziende non ancora iscritte.")

    st.markdown("---")
    st.markdown("### 🔍 Domande & Keyword Più Cercate dai Clienti Finali a Catania")

    col_kw1, col_kw2, col_kw3 = st.columns(3)
    with col_kw1:
        st.markdown("**Riscaldamento & Caldaie**")
        st.markdown("""
        - `assistenza caldaie catania h24`
        - `blocco caldaia vaillant acireale`
        - `costo bollino blu caldaia catania`
        - `tecnico caldaie ariston catania`
        """)
    with col_kw2:
        st.markdown("**Climatizzazione**")
        st.markdown("""
        - `ricarica condizionatore catania subito`
        - `installazione climatizzatori acireale`
        - `condizionatore non raffredda misterbianco`
        - `preventivo dual split catania`
        """)
    with col_kw3:
        st.markdown("**Idraulica & Elettrico**")
        st.markdown("""
        - `idraulico pronto intervento catania`
        - `riparazione perdita acqua acireale`
        - `elettricista urgente catania h24`
        - `certificazione conformità impianto 37/08`
        """)


# ==========================================
# TAB 3: CONTENUTI & SALES HUB
# ==========================================
with tab_content:
    st.subheader("Sales Hub & Contenuti Pronti all'Uso")
    st.markdown("Materiali di vendita, script di telemarketing, template WhatsApp e calcolatore ROI.")

    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs([
        "📞 Script Telefonici",
        "💬 Template WhatsApp",
        "🧮 Calcolatore ROI",
        "🛡️ Risoluzione Obiezioni"
    ])

    with sub_t1:
        st.markdown("#### Script Telefonico 1: Aziende già Associate a CNA (Sconto Convenzione)")
        st.code("""
Operatore: "Buongiorno [Nome Titolare/Azienda], la chiamo da TecnicoLIVE. La contatto in merito alla convenzione ufficiale attiva con CNA Catania per le aziende impiantistiche.
Sappiamo che in questo periodo siete spesso in cantiere con le mani occupate e molte telefonate di clienti finiscono senza risposta.
Con la convenzione CNA Catania le abbiamo riservato l'assistente vocale AI che risponde H24 ai suoi clienti, prende gli appuntamenti e le invia la notifica WhatsApp con diagnosi del guasto, con canone agevolato categoria CNA.
Ha 5 minuti oggi alle 17:00 per fare una prova live chiamando il nostro numero test?"
        """, language="markdown")

        st.markdown("#### Script Telefonico 2: Aziende NON Associate (Leva Doppio Valore)")
        st.code("""
Operatore: "Buongiorno [Nome Titolare], chiamo da TecnicoLIVE. Stiamo attivando nella zona di [Comune] la convenzione esclusiva con CNA Catania per gli impiantisti.
Abbiamo notato che non siete ancora registrati negli elenchi soci CNA: per supportare le ditte del territorio abbiamo creato un pacchetto speciale.
Vi attiviamo l'assistente vocale per recuperare tutte le chiamate che perdete mentre siete sui furgoni e, contemporaneamente, sblocchiamo il vostro tesseramento agevolato a CNA Catania con tutti i vantaggi fiscali e legali di categoria.
Chi si occupa in azienda di decidere sulle chiamate e sulla gestione dei clienti?"
        """, language="markdown")

    with sub_t2:
        st.markdown("#### Messaggi WhatsApp Brevi ad Alto Tasso di Risposta")
        st.info("💡 Suggerimento: inviare tra le 12:30 e le 14:00 o dopo le 18:00, quando il tecnico ha terminato gli interventi sul campo.")

        st.markdown("**Opzione 1: Per Caldaisti e Idraulici**")
        st.code("""
Ciao [Nome], ti scrivo da TecnicoLIVE (partner CNA Catania). 
Quante chiamate di nuovi clienti perdi ogni settimana mentre sei sotto una caldaia o in cantiere con le mani occupate?
Il nostro assistente vocale AI risponde per te in 3 secondi, fa la pre-diagnosi del guasto e ti prenota l'intervento su WhatsApp.
👉 Ascolta come risponde con la voce di un tecnico vero: https://www.tecnicolive.it
Possiamo attivarti una prova gratuita di 7 giorni con la convenzione CNA. Ti lascio il link per testarlo?
        """, language="markdown")

        st.markdown("**Opzione 2: Follow-up Veloce**")
        st.code("""
[Nome], una chiamata persa è un cliente regalato alla concorrenza. 
In provincia di Catania abbiamo già attivato oltre 60 colleghi impiantisti che non perdono più un lavoro. 
Se hai 2 minuti ti faccio squillare il centralino dimostrativo per vedere come prende l'appuntamento da solo.
        """, language="markdown")

    with sub_t3:
        st.markdown("#### 🧮 Calcolatore ROI Interattivo del Fatturato Perso")
        st.markdown("Usa questo calcolatore durante la chiamata per quantificare il denaro che il cliente sta perdendo ogni mese:")

        col_roi1, col_roi2 = st.columns(2)
        with col_roi1:
            num_tecnici = st.slider("Numero di tecnici / furgoni in azienda:", min_value=1, max_value=15, value=2)
            chiamate_perse_settimana = st.slider("Chiamate inevase stimate a settimana per tecnico:", min_value=2, max_value=25, value=8)
            valore_medio_intervento = st.number_input("Valore medio di un intervento (€):", min_value=50, max_value=1500, value=120, step=10)
            tasso_conversione_chiamate = st.slider("% di chiamate perse che sarebbero diventate lavoro:", min_value=10, max_value=80, value=30) / 100.0

        with col_roi2:
            chiamate_perse_mese = chiamate_perse_settimana * 4 * num_tecnici
            interventi_persi_mese = chiamate_perse_mese * tasso_conversione_chiamate
            fatturato_perso_mese = interventi_persi_mese * valore_medio_intervento
            fatturato_perso_anno = fatturato_perso_mese * 12

            costo_tecnicolive_anno = 239 * 12  # Piano PRO annuale
            guadagno_netto = fatturato_perso_anno - costo_tecnicolive_anno
            roi_moltiplicatore = (guadagno_netto / costo_tecnicolive_anno) if costo_tecnicolive_anno > 0 else 0

            st.markdown(f"""
            <div style="background: #FFF5F5; border: 1px solid #FEB2B2; border-radius: 8px; padding: 15px; margin-bottom: 12px;">
                <div style="font-size: 0.85rem; font-weight: 700; color: #9B2C2C; text-transform: uppercase;">Perdita Economica Attuale</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #E53E3E;">-{fatturato_perso_mese:,.0f} € / mese</div>
                <div style="font-size: 0.9rem; color: #742A2A;">Pari a <strong>-{fatturato_perso_anno:,.0f} € all'anno</strong> in interventi persi</div>
            </div>

            <div style="background: #F0FFF4; border: 1px solid #9AE6B4; border-radius: 8px; padding: 15px;">
                <div style="font-size: 0.85rem; font-weight: 700; color: #22543D; text-transform: uppercase;">Ritorno sull'Investimento TecnicoLIVE</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #276749;">+{guadagno_netto:,.0f} € / anno</div>
                <div style="font-size: 0.9rem; color: #22543D;">ROI: <strong>{roi_moltiplicatore:.1f}x</strong> (investi 1€, ne recuperi {roi_moltiplicatore:.1f}€)</div>
            </div>
            """, unsafe_allow_html=True)

    with sub_t4:
        st.markdown("#### 🛡️ Battlecard: Risoluzione delle Obiezioni Più Comuni")

        with st.expander("🗣️ Obiezione 1: 'Risponde già mia moglie / ho già una segretaria'"):
            st.markdown("""
            **Risposta vincente:**  
            *"Perfetto, TecnicoLIVE non sostituisce la segretaria, ma la potenzia! Quando la segretaria è al telefono su una linea e arriva un'altra chiamata, cosa succede? Il secondo cliente trova occupato e chiama un'altra ditta. Con TecnicoLIVE gestite fino a 10 chiamate contemporaneamente, e fuori orario (la sera, nel weekend e nei festivi) l'IA risponde per voi filtrando solo le vere emergenze calde."*
            """)

        with st.expander("🗣️ Obiezione 2: 'I clienti vogliono parlare direttamente con me'"):
            st.markdown("""
            **Risposta vincente:**  
            *"La capisco benissimo, ma quando lei è con le mani dentro una caldaia accesa o sta guidando sul raccordo, non può rispondere tecnicamente a fondo. Il nostro assistente vocale dice: 'Buongiorno, sono l'assistente del Sig. [Cognome], in questo momento è su un intervento urgente. Mi dica il guasto che le apro la scheda e la faccio richiamare con la diagnosi pronta'. Il cliente si sente subito accolto invece di trovare la segreteria telefonica muta."*
            """)

        with st.expander("🗣️ Obiezione 3: 'Costa troppo'"):
            st.markdown("""
            **Risposta vincente:**  
            *"Con un canone convenzionato CNA di circa 7€ al giorno, basta recuperare **un solo intervento al mese** (che vale in media 120-250€) per ripagarsi interamente il sistema per tutto l'anno. Tutto il resto è guadagno puro che oggi state lasciando ai concorrenti."*
            """)

        with st.expander("🗣️ Obiezione 4: 'L'Intelligenza Artificiale sbaglia / sembra un robot finto'"):
            st.markdown("""
            **Risposta vincente:**  
            *"Non è la solita voce metallica con 'premere 1 per...'. La nostra IA ha tempi di risposta sub-600ms, parla italiano fluido, comprende il dialetto e i termini tecnici come 'blocco F28', 'termocoppia' o 'perdita raccordo'. Facciamo una prova adesso: le invio il link e la chiami lei stesso per giudicare."*
            """)

# Footer informativo
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94A3B8; font-size: 0.8rem; padding-bottom: 20px;">
    TecnicoLIVE &bull; Sinergia Rete d'Imprese &bull; Piazza dei Martiri 8, 95131 Catania (CT) &bull; Partnership Istituzionale con CNA Catania
</div>
""", unsafe_allow_html=True)
