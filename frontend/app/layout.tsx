import type { Metadata } from "next";
import Nav from "../components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kraken Trading Agent",
  description: "Natural-language Kraken limit order interface",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
