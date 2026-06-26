import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Healthy Aging Policy Observatory",
  description:
    "Canadian Healthy Aging Policy Observatory — monitor, quantify, and evaluate aging policy across Canadian governments.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
