import argparse
import asyncio
import sys
from src.pipeline import run_pipeline
from src.lead_finder import discover_new_leads, save_discovered_leads
from src.massive_lead_scraper import run_territory_scan
from src.territory_data import CATANIA_MUNICIPALITIES


def main():
    parser = argparse.ArgumentParser(description="Lead Finder & CNA Catania Affiliation Verifier (TecnicoLIVE)")
    parser.add_argument("--deep-scan", action="store_true", help="Esegue la scansione massiva a tappeto di TUTTI i 58 comuni della provincia di Catania senza limiti")
    parser.add_argument("--area", type=str, default=None, help="Filtra la scansione su una macro-area specifica (es. acese, metropolitana, industriale, calatino, jonico)")
    parser.add_argument("--discover", action="store_true", help="Cerca attivamente nuovi lead sui settori chiave a Catania e provincia")
    parser.add_argument("--city", type=str, default=None, help="Comune specifico su cui focalizzare la ricerca (es. acireale, misterbianco)")
    parser.add_argument("--all-cities", action="store_true", help="Scandaglia i principali comuni della provincia")
    parser.add_argument("--pdf", action="store_true", help="Genera il report PDF strategico con metriche, proiezioni MRR e churn rate")
    parser.add_argument("--max-per-sector", type=int, default=10, help="Numero massimo di lead per settore nella modalità discover rapida (default: 10)")
    parser.add_argument("--limit", type=int, default=0, help="Limita il numero di lead da elaborare nella pipeline di verifica (0 = tutte)")
    args = parser.parse_args()

    print("=" * 75)
    print("   LEAD FINDER TECNICOLIVE & CNA CATANIA")
    print("   Scansione Territoriale Massiva (58 Comuni) & Verifica CNA")
    print("=" * 75)
    
    if args.pdf:
        print("Modalità: GENERAZIONE REPORT PDF STRATEGICO CON PROIEZIONI MRR\n")
        from src.generate_pdf_report import generate_pdf
        asyncio.run(generate_pdf())

    elif args.deep_scan:
        selected_munis = CATANIA_MUNICIPALITIES
        if args.area:
            area_term = args.area.lower().strip()
            selected_munis = [m for m in CATANIA_MUNICIPALITIES if area_term in m["area"].lower()]
            print(f"Filtro macro-area attivo: '{args.area}' ({len(selected_munis)} comuni selezionati)")
        else:
            print(f"Modalità: DEEP SCAN PROVINCIALE COMPLETO (Tutti i {len(selected_munis)} comuni della provincia)")
            
        print("Scansione iterativa sulle 12 query impiantistiche fino a esaurimento risultati (nessun limite).")
        print("Deduplica automatica in tempo reale rispetto al database.\n")
        
        async def run_massive():
            df_new = await run_territory_scan(selected_municipalities=selected_munis, verify_cna=True)
            save_discovered_leads(df_new)
            print(f"\nScansione massiva completata! Aggiunte {len(df_new)} nuove aziende.")
            # Rigenera PDF finale con i nuovi totali
            from src.generate_pdf_report import generate_pdf
            await generate_pdf()
            
        asyncio.run(run_massive())

    elif args.discover:
        target_label = f"Comune: {args.city.upper()}" if args.city else ("TUTTI I PRINCIPALI COMUNI" if args.all_cities else "Catania")
        print(f"Modalità: DISCOVERY NUOVI LEAD ({target_label} - max {args.max_per_sector} per settore)")
        print("Settori: HVAC/Clima, Caldaie, Termoidraulica, Elettrico, Impianti Industriali\n")
        
        async def run_discovery():
            df_new = await discover_new_leads(
                max_leads_per_sector=args.max_per_sector,
                verify_with_crawl4ai=True,
                target_city=args.city,
                all_cities=args.all_cities
            )
            save_discovered_leads(df_new)
            print(f"\nOperazione completata! Trovate {len(df_new)} nuove aziende qualificate.")
            
        asyncio.run(run_discovery())

    else:
        if args.limit > 0:
            print(f"Modalità: VERIFICA LEAD ESISTENTI (limitata a {args.limit} lead)")
        else:
            print("Modalità: VERIFICA LEAD ESISTENTI (tutte le lead in CSV_Leads/)")
        asyncio.run(run_pipeline(limit=args.limit))


if __name__ == "__main__":
    main()
