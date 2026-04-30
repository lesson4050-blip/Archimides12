import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Archimedes",
  description: "Archimedes — Beyond Intelligence",
};

import ThemeInitializer from "@/components/ThemeInitializer";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ThemeInitializer />
        {children}
      </body>
    </html>
  );
}
