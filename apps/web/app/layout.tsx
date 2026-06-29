import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { LogoMark } from "@/components/Logo";

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
      </body>
    </html>
  );
}
