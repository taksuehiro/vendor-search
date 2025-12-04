import "./../styles/globals.css";
import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";

export const metadata = { title: "TTCDX Knowledge Search" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body className="min-h-screen">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
