import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Manak Setu मानक सेतु — Standards Bridge",
  description: "AI-powered recommendation engine for applicable Indian Standards (SIH26108). Type or speak any tender need, get verified standards, versions and certification duties.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Tiro+Devanagari+Hindi&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="tricolor" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
