import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SchemePath — Find Your Government Benefits",
  description:
    "SchemePath uses AI to help Indian citizens discover and navigate government schemes they are eligible for, step by step.",
  keywords: ["government schemes", "india", "eligibility", "PM-KISAN", "Ayushman Bharat"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen antialiased">
        <div className="relative flex min-h-screen flex-col">{children}</div>
      </body>
    </html>
  );
}
