import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LogoMark } from "@/components/Logo";
import { APP_VERSION } from "@/lib/version";
import {
  GITHUB_REPO_URL,
  SITE_URL,
  SITE_NAME,
  SITE_SHORT,
  SITE_DESCRIPTION,
  SITE_KEYWORDS,
  GITHUB_PROFILE_URL,
} from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — HAIL Lab`,
    template: `%s · ${SITE_SHORT}`,
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: SITE_KEYWORDS,
  authors: [{ name: "Giorgio Huang", url: GITHUB_PROFILE_URL }],
  creator: "Healthy Aging Intelligence Lab (HAIL)",
  publisher: "Healthy Aging Intelligence Lab (HAIL)",
  category: "science",
  alternates: { canonical: "/" },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: `${SITE_NAME} — HAIL Lab`,
    description: SITE_DESCRIPTION,
    url: "/",
    locale: "en_CA",
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} — HAIL Lab`,
    description: SITE_DESCRIPTION,
  },
};

const NAV: Array<{ href: string; label: string }> = [
  { href: "/", label: "Dashboard" },
  { href: "/policies", label: "Policy Library" },
  { href: "/data", label: "Data Hub" },
  { href: "/hapi", label: "HAPI" },
  { href: "/analytics", label: "Analytics" },
  { href: "/assistant", label: "Assistant" },
];

// Organization + WebSite structured data (JSON-LD). Helps search engines
// understand the publisher and enables a sitelinks search box / richer results.
const STRUCTURED_DATA = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: "Healthy Aging Intelligence Lab (HAIL)",
      alternateName: SITE_SHORT,
      url: SITE_URL,
      description: SITE_DESCRIPTION,
      sameAs: [GITHUB_REPO_URL, GITHUB_PROFILE_URL],
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: SITE_NAME,
      url: SITE_URL,
      description: SITE_DESCRIPTION,
      inLanguage: "en-CA",
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <script
          type="application/ld+json"
          // Static, non-user data — safe to inline as JSON-LD.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(STRUCTURED_DATA) }}
        />
        <header className="topnav">
          <div className="topnav-inner">
            <Link href="/" className="brand" aria-label="Healthy Aging Policy Observatory — home">
              <LogoMark size={24} />
              <span className="brand-text">
                HAPI<span className="brand-dim"> · Observatory</span>
              </span>
            </Link>
            <nav>
              {NAV.map((item) => (
                <Link key={item.href} href={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        {children}
        <footer className="site-footer">
          <div className="site-footer-inner">
            <div className="footer-brand">
              <LogoMark size={18} />
              <span>Canadian Healthy Aging Policy Observatory</span>
            </div>
            <nav className="footer-links">
              <Link href="/about">About</Link>
              <Link href="/research">Research</Link>
              <a href={GITHUB_REPO_URL} target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </nav>
            <p className="footer-note">
              <span className="footer-sentence">
                Every figure traces to its source; association is not causation.
              </span>{" "}
              <span className="footer-sentence">
                © 2026 Healthy Aging Intelligence Lab (HAIL)
              </span>
            </p>
            <p className="footer-version">build {APP_VERSION}</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
