import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Manak Setu — Standards Bridge",
  description: "AI-powered recommendation engine for applicable Indian Standards (SIH26108)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
