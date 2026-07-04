import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LogoMark } from "@/components/Logo";
import { GITHUB_REPO_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Healthy Aging Policy Observatory",
  description:
    "Canadian Healthy Aging Policy Observatory — monitor, quantify, and evaluate aging policy across Canadian governments.",
};

const NAV: Array<{ href: string; label: string }> = [
  { href: "/", label: "Dashboard" },
  { href: "/policies", label: "Policy Library" },
  { href: "/data", label: "Data Hub" },
  { href: "/hapi", label: "HAPI" },
  { href: "/analytics", label: "Analytics" },
  { href: "/assistant", label: "Assistant" },
  { href: "/about", label: "About" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
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
              <Link href="/data">Data Hub</Link>
              <Link href="/hapi">HAPI</Link>
              <a href={GITHUB_REPO_URL} target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </nav>
            <p className="footer-note">
              <span className="footer-sentence">
                Part of the Healthy Aging Intelligence Lab (HAIL).
              </span>{" "}
              <span className="footer-sentence">
                Every figure traces to its source; association is not causation.
              </span>{" "}
              <span className="footer-sentence">© {new Date().getFullYear()}</span>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
