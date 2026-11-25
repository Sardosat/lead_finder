import pandas as pd
import re
import os

def clean_phone(phone_val):
    if pd.isna(phone_val):
        return ""
    p = str(phone_val).strip()
    if p.endswith('.0'):
        p = p[:-2]
    digits = re.sub(r'[^\d]', '', p)
    if not digits:
        return ""
    if digits.startswith('0039'):
        digits = digits[4:]
    elif digits.startswith('39') and len(digits) >= 11:
        digits = digits[2:]
    return f"+39{digits}"

def generate_tags(row):
    tags = ["leadfinder-tecnicolive", "catania-termoidraulica"]
    
    stato = str(row.get('Stato_CNA', ''))
    if "ASSOCIATO RILEVATO" in stato:
        tags.append("gancio-tecnicolive-diretto")
        tags.append("socio-cna-rilevato")
        tags.append("convenzione-cna")
    else:
        tags.append("gancio-verifica-cna")
        if "NON ASSOCIATO" in stato:
            tags.append("non-associato")
            tags.append("target-tesseramento-cna")
        else:
            tags.append("da-verificare")
            
    tier = str(row.get('Lead_Tier', ''))
    if "Tier A" in tier:
        tags.append("tier-a-vip")
    elif "Tier B" in tier:
        tags.append("tier-b-warm")
    elif "Tier C" in tier:
        tags.append("tier-c-cold")
        
    city = str(row.get('City', '')).strip().lower().replace(" ", "-").replace("'", "")
    if city and city != "nan":
        tags.append(f"comune-{city}")
        
    marchi = str(row.get('Marchi_Rilevati', ''))
    if marchi and marchi != "nan":
        for m in [x.strip().lower() for x in marchi.split(',')]:
            if m:
                tags.append(f"brand-{m}")
                
    return ", ".join(tags)

def generate_notes(row):
    company = str(row.get('Company Name', '')).strip()
    stato = str(row.get('Stato_CNA', '')).strip()
    piva = str(row.get('Partita_IVA', '')).strip()
    marchi = str(row.get('Marchi_Rilevati', '')).strip()
    h24 = str(row.get('Servizio_H24', '')).strip()
    score = str(row.get('ICP_Score', '')).strip()
    tier = str(row.get('Lead_Tier', '')).strip()
    icebreaker = str(row.get('Icebreaker_1to1', '')).strip()
    pitch = str(row.get('Pitch_Commerciale_TecnicoLIVE', '')).strip()
    
    gancio_tipo = "GANCIO 1: DIRETTO TECNICOLIVE (Socio CNA rilevato)" if "ASSOCIATO RILEVATO" in stato else "GANCIO 2: VERIFICA CNA & TESSERAMENTO AGEVOLATO"
    
    notes = f"""=== SCHEDA GUIDA OPERATORE TECNICOLIVE ===
AZIENDA: {company}
COMUNE: {row.get('City', '')}
P.IVA: {piva if piva and piva != 'nan' else 'Non rilevata'}
ICP SCORE: {score}/100 ({tier})
MARCHI: {marchi if marchi and marchi != 'nan' else 'Multimarca'}
REPERIBILITÀ H24: {h24}
STATO CNA: {stato}

TIPO DI APPROCCIO: {gancio_tipo}

--- SCRIPT VOCALE / WHATSAPP (1-TO-1) ---
{icebreaker}

--- PITCH COMMERCIALE GUIDATO ---
{pitch}

--- CONDIZIONI CONVENZIONE CNA CATANIA ---
• Assistente Vocale AI TecnicoLIVE: Risposta H24 su linea 095 dedicata o deviazione
• Prova Gratuita: 7 Giorni senza carta di credito
• Canone Convenzione Soci CNA: Agevolato (€269/mese anziché tariffa standard)
• Per Non Associati: Sconto 50% sulla prima quota annuale di tesseramento CNA Catania inclusa nell'attivazione.
=========================================
"""
    return notes.strip()

def main():
    df = pd.read_csv('data/tutte_le_lead.csv')
    print(f"Loaded {len(df)} leads.")
    
    records = []
    for _, row in df.iterrows():
        comp_name = str(row.get('Company Name', '')).strip()
        phone = clean_phone(row.get('Phone', ''))
        tags = generate_tags(row)
        notes = generate_notes(row)
        
        # Split names if simple personal name, else Company Name
        first_name = comp_name
        last_name = ""
        if comp_name.startswith("Ditta "):
            last_name = comp_name.replace("Ditta ", "").strip()
            first_name = "Titolare"
            
        rec = {
            "First Name": first_name,
            "Last Name": last_name,
            "Company Name": comp_name,
            "Phone": phone,
            "Email": str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else "",
            "Address": str(row.get('Address', '')).strip() if pd.notna(row.get('Address')) else "",
            "City": str(row.get('City', '')).strip() if pd.notna(row.get('City')) else "",
            "Partita IVA": str(row.get('Partita_IVA', '')).strip() if pd.notna(row.get('Partita_IVA')) else "",
            "Tags": tags,
            "Notes": notes,
            "Opportunity Name": f"{comp_name} - TecnicoLIVE",
            "Opportunity Pipeline": "TecnicoLIVE - Outbound & Convenzione CNA Catania",
            "Opportunity Stage": "[01] 📥 Nuova Lead Assegnata (Da Contattare)",
            "Opportunity Status": "open",
            "Opportunity Value": "269"
        }
        records.append(rec)
        
    df_out = pd.DataFrame(records)
    
    # 1. Pilot CSV with 4 leads (1 associate + 3 non-associates)
    lead1 = df_out[df_out['Company Name'] == 'Tecs Srl']
    lead2 = df_out[df_out['Company Name'] == 'Clima Business Palma']
    lead3 = df_out[df_out['Company Name'] == 'Caldaie Catania']
    lead4 = df_out[df_out['Company Name'].str.contains('Cantarella Clima', case=False, na=False)].head(1)
    
    df_pilot = pd.concat([lead1, lead2, lead3, lead4], ignore_index=True)
    df_pilot.to_csv('data/RSK_PILOTA_4_LEAD.csv', index=False, encoding='utf-8-sig')
    df_pilot.to_csv('data/RSK_PILOTA_2_LEAD.csv', index=False, encoding='utf-8-sig') # keep compatibility
    print(f"Created data/RSK_PILOTA_4_LEAD.csv with {len(df_pilot)} pilot records:")
    for _, r in df_pilot.iterrows():
        print(f" - {r['Company Name']} | Phone: {r['Phone']} | Tags: {r['Tags'][:60]}...")
        
    # 2. Complete CSV
    df_out.to_csv('data/RSK_IMPORT_TECNICOLIVE_COMPLETO.csv', index=False, encoding='utf-8-sig')
    print(f"\nCreated data/RSK_IMPORT_TECNICOLIVE_COMPLETO.csv with {len(df_out)} total records.")

if __name__ == '__main__':
    main()
