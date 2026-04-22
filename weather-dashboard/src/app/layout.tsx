import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Quantum Weather Terminal",
  description: "Advanced weather trading bot monitoring dashboard",
  keywords: ["weather", "trading", "prediction", "dashboard", "quantum", "fintech"],
  authors: [{ name: "Claude" }],
  creator: "Claude Code",
  themeColor: "#020617",
  viewport: "width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes",
  robots: "index, follow",
  openGraph: {
    title: "Quantum Weather Terminal",
    description: "Advanced weather trading bot monitoring dashboard",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Quantum Weather Terminal",
    description: "Advanced weather trading bot monitoring dashboard",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased dark`}
    >
      <head>
        <meta charSet="utf-8" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body className="min-h-full bg-background text-foreground scanlines">
        <div className="relative min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
