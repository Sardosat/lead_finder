import argparse
import asyncio
import json

from src.clean_existing_data import run_data_cleanup
from src.lead_finder import discover_new_leads, save_discovered_leads
from src.massive_lead_scraper import run_territory_scan
from src.pipeline import run_pipeline
from src.territory_data import CATANIA_MUNICIPALITIES


async def _run_pdf_generation(target: str):
    target_norm = (target or "all").lower().strip()
    if target_norm in ("strategico", "all"):
        from src.generate_pdf_report import generate_pdf
        await generate_pdf()
    if target_norm in ("termoidraulica", "all"):
        from src.generate_termoidraulica_pdf import generate_termoidraulica_pdf
        await generate_termoidraulica_pdf()
    if target_norm in ("top100", "all"):
        from src.generate_top100_pdf import generate_top100_pdf
        await generate_top100_pdf()


async def _run_vies(vat_id: str):
    from engine.connectors.vies_validator import ViesValidatorClient

    client = ViesValidatorClient()
    res = await client.check_vat(vat_id)
    print(json.dumps(res, indent=2, ensure_ascii=False))


async def _run_tech_audit(url: str):
    from engine.enrichment.tech_audit import TechAuditor

    auditor = TechAuditor()
    res = await auditor.audit_website(url, check_mx=True)
    print(json.dumps(res.model_dump(), indent=2, ensure_ascii=False))


async def _run_openapi_check(vat_or_cf: str):
    from engine.connectors.openapi_italy import OpenapiItalyClient

    client = OpenapiItalyClient(max_budget_eur=1.0)
    res = await client.query_company(vat_or_cf, endpoint="IT-start")
    print(json.dumps(res, indent=2, ensure_ascii=False))


async def _run_engine_demo():
    from engine.enrichment.pipeline_runner import EnrichmentPipelineRunner
    from engine.exporters.webhook_exporter import build_webhook_payload
    from engine.schemas.campaign import CampaignConfig, EnrichmentLevels, GeoFilter
    from engine.schemas.lead import LeadRecord

    campaign = CampaignConfig(
        campaign_id="demo_multi_prodotto_it",
        name="Demo Multi-Prodotto IT/EU vs Clay",
        target_vertical="PMI Multisettore Italia",
        search_queries=["impiantisti Catania", "agenzia marketing Palermo"],
        geo=GeoFilter(country_code="IT", province_code="CT", municipalities=["Catania", "Valverde"]),
        offer_summary="Routing automatico MonetizeLab / RSK System / TecnicoLIVE con conformità GDPR LIA",
        enrichment=EnrichmentLevels(
            enable_l1_tech_audit=False,
            enable_l1_mx_check=False,
            enable_l1_vies=False,
            enable_l2_gemini_ai=False,
            enable_l3_openapi_registry=False,
        ),
    )

    seeds = [
        LeadRecord(
            company_name="Tesalia cbc",
            country_code="EC",
            city="Desvío Puente Morán Valverde",
            address="Pichincha, Ecuador",
            category="Food and Beverage Services",
        ),
        LeadRecord(
            company_name="Etna Media Digital Agency Srl",
            country_code="IT",
            province="CT",
            city="Catania",
            vat_id="IT01234567897",
            phone_e164="+393471234567",
            email="info@etnamedia.it",
            website="https://etnamedia.it",
            category="Agenzia Marketing Digitale",
        ),
        LeadRecord(
            company_name="Clima Service Etnea Srl",
            country_code="IT",
            province="CT",
            city="Valverde",
            address="Via Etnea 10, 95028 Valverde (CT)",
            vat_id="IT06200390877",
            phone_e164="+393487654321",
            email="amministrazione@climaserviceetnea.it",
            pec="climaservice@pec.it",
            website="https://climaserviceetnea.it",
            category="Termoidraulica e Caldaie",
        ),
        LeadRecord(
            company_name="Clinica Sorriso Catania Srl",
            country_code="IT",
            province="CT",
            city="Catania",
            vat_id="IT01112223334",
            phone_e164="+390951234567",
            email="clinica@pec.legalmail.it",
            website="https://clinicasorriso.it",
            category="Studio Dentistico",
        ),
    ]

    runner = EnrichmentPipelineRunner()
    result = await runner.run_campaign(campaign, seed_leads=seeds)
    leads = result["leads"]
    payload = build_webhook_payload(campaign.campaign_id, leads)

    print(f"Stats Pipeline: {json.dumps(result['stats'], ensure_ascii=False)}")
    for ld in leads:
        print(
            f" - {ld.company_name} ({ld.city}) -> Prodotto: {ld.ai_qualification.recommended_product} "
            f"[{ld.ai_qualification.recommended_product_url}] | LIA={ld.lia.status if ld.lia else 'N/D'} "
            f"| PEC_Blocked={ld.lia.pec_cold_outreach_blocked if ld.lia else False} | Email={ld.email or 'BLOCKED_PEC'}"
        )
    print(f"Webhook Draft Eligible={payload['eligible_count']} | Skipped={payload['skipped_blocked_count']}")


def main():
    parser = argparse.ArgumentParser(
        description="Lead Intelligence Engine IT/EU & CNA Catania Verifier"
    )
    parser.add_argument("--clean", action="store_true", help="Bonifica, deduplica, normalizzazione E.164 e sync CSV/Excel")
    parser.add_argument("--crawl", action="store_true", help="Usato con --clean: crawl live sui siti aziendali reali")
    parser.add_argument("--deep-scan", action="store_true", help="Scansione massiva provinciale (58 comuni Catania)")
    parser.add_argument("--area", type=str, default=None, help="Filtra scansione su una macro-area")
    parser.add_argument("--discover", action="store_true", help="Ricerca attiva nuovi lead sui settori chiave")
    parser.add_argument("--city", type=str, default=None, help="Comune specifico (es. acireale)")
    parser.add_argument("--all-cities", action="store_true", help="Scandaglia i principali comuni della provincia")
    parser.add_argument(
        "--pdf",
        nargs="?",
        const="all",
        choices=["strategico", "termoidraulica", "top100", "all"],
        default=None,
        help="Genera i report PDF (strategico, termoidraulica, top100, oppure all)",
    )
    parser.add_argument("--max-per-sector", type=int, default=10, help="Limite per settore in --discover")
    parser.add_argument("--limit", type=int, default=0, help="Limite lead per la pipeline CSV_Leads/")
    parser.add_argument("--vies", type=str, default=None, help="Verifica live P.IVA tramite VIES Commissione Europea")
    parser.add_argument("--tech-audit", type=str, default=None, help="Esegue Livello 1 Tech Audit + DNS MX su un URL")
    parser.add_argument("--openapi-check", type=str, default=None, help="Interroga Openapi.com IT-start su P.IVA/CF")
    parser.add_argument("--engine-demo", action="store_true", help="Esegue demo end-to-end del nuovo Lead Engine IT/EU")
    args = parser.parse_args()

    print("=" * 75)
    print("   LEAD INTELLIGENCE ENGINE IT/EU • TECNICOLIVE • RSK • MONETIZELAB")
    print("=" * 75)

    if args.vies:
        asyncio.run(_run_vies(args.vies))
    elif args.tech_audit:
        asyncio.run(_run_tech_audit(args.tech_audit))
    elif args.openapi_check:
        asyncio.run(_run_openapi_check(args.openapi_check))
    elif args.engine_demo:
        asyncio.run(_run_engine_demo())
    elif args.clean:
        mode = "CON CRAWL LIVE SITI REALI" if args.crawl else "OFFLINE (CACHE + NORMALIZZAZIONE)"
        print(f"Modalità: BONIFICA & SINCRONIZZAZIONE DATASET ({mode})\n")
        summary = asyncio.run(run_data_cleanup(live_crawl=args.crawl))
        print(f"\nBonifica completata: {summary}")
    elif args.pdf:
        print(f"Modalità: GENERAZIONE REPORT PDF ({args.pdf.upper()})\n")
        asyncio.run(_run_pdf_generation(args.pdf))
    elif args.deep_scan:
        selected_munis = CATANIA_MUNICIPALITIES
        if args.area:
            area_term = args.area.lower().strip()
            selected_munis = [m for m in CATANIA_MUNICIPALITIES if area_term in m["area"].lower()]
            print(f"Filtro macro-area attivo: '{args.area}' ({len(selected_munis)} comuni selezionati)")
        else:
            print(f"Modalità: DEEP SCAN PROVINCIALE COMPLETO ({len(selected_munis)} comuni)")

        async def run_massive():
            df_new = await run_territory_scan(selected_municipalities=selected_munis, verify_cna=True)
            save_discovered_leads(df_new)
            print(f"\nScansione massiva completata! Aggiunte {len(df_new)} nuove aziende.")
            await _run_pdf_generation("all")

        asyncio.run(run_massive())
    elif args.discover:
        target_label = f"Comune: {args.city.upper()}" if args.city else (
            "TUTTI I PRINCIPALI COMUNI" if args.all_cities else "Catania"
        )
        print(f"Modalità: DISCOVERY NUOVI LEAD ({target_label} - max {args.max_per_sector} per settore)")

        async def run_discovery():
            df_new = await discover_new_leads(
                max_leads_per_sector=args.max_per_sector,
                verify_with_crawl4ai=True,
                target_city=args.city,
                all_cities=args.all_cities,
            )
            save_discovered_leads(df_new)
            print(f"\nOperazione completata! Trovate {len(df_new)} nuove aziende qualificate.")

        asyncio.run(run_discovery())
    else:
        print("Modalità: VERIFICA LEAD ESISTENTI (CSV_Leads/)")
        asyncio.run(run_pipeline(limit=args.limit))


if __name__ == "__main__":
    main()
