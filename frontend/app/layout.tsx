import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DecisionOS | Operations Control",
  description: "Pharmaceutical supply-chain decision control system",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}