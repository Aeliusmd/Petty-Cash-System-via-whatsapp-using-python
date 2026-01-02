import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Petty Cash Admin",
  description: "Petty Cash Management System - Admin Panel",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-900 text-gray-100`}
      >
        <div className="min-h-screen">
          {/* Header */}
          <header className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg">
            <div className="max-w-7xl mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <Link href="/" className="flex items-center gap-3">
                  <span className="text-2xl">💰</span>
                  <h1 className="text-xl font-bold">Petty Cash Admin</h1>
                </Link>
                <nav className="flex gap-6">
                  <Link href="/" className="hover:text-indigo-200 transition-colors font-medium">
                    Dashboard
                  </Link>
                  <Link href="/claims" className="hover:text-indigo-200 transition-colors font-medium">
                    Claims
                  </Link>
                  <Link href="/employees" className="hover:text-indigo-200 transition-colors font-medium">
                    Employees
                  </Link>
                </nav>
              </div>
            </div>
          </header>

          {/* Main Content */}
          <main className="max-w-7xl mx-auto px-4 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
