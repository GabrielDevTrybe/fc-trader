import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'FC Trader | Financial Market Terminal for EA FC 27',
  description: 'Terminal de análise quantitativa de mercado e oportunidades de trading para EA SPORTS FC 27 Ultimate Team.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
