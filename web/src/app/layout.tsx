import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "Lead Intelligence Engine IT/EU — TecnicoLIVE & Ecosistema PMI",
  description:
    "Piattaforma operativa stile Clay per il mercato italiano ed europeo: Lead Finder, Trend Finder, Archivio Export e conformità GDPR.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
