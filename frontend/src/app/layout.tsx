'use client';

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

function LayoutContent({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin, isManager, isSuperAdmin, isInOrganization, user, logout, exitOrganization } = useAuth();

  // Super admin without org context - show only organizations
  const showOnlyOrganizations = isSuperAdmin && !isInOrganization;

  return (
    <div className="min-h-screen">
      {/* Only show header/navigation when authenticated */}
      {isAuthenticated && (
        <header className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <Link href={showOnlyOrganizations ? "/organizations" : "/"} className="flex items-center gap-3">
                <span className="text-2xl">💰</span>
                <h1 className="text-xl font-bold">Petty Cash System</h1>
              </Link>
              <nav className="flex items-center gap-6">
                
                {/* Super Admin Mode - Show only Organizations */}
                {showOnlyOrganizations ? (
                  <Link href="/organizations" className="hover:text-indigo-200 transition-colors font-medium">
                    🏢 Organizations
                  </Link>
                ) : (
                  <>
                    {/* Organization Context Indicator - Only show Exit for super admin */}
                    {isInOrganization && (
                      <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-lg mr-2">
                        <span className="text-sm">📍 {user?.organization_name}</span>
                        {isSuperAdmin && (
                          <button
                            onClick={exitOrganization}
                            className="text-xs bg-white/20 hover:bg-white/30 px-2 py-0.5 rounded transition-colors"
                          >
                            Exit
                          </button>
                        )}
                      </div>
                    )}

                    {/* Dashboard - All roles */}
                    <Link href="/" className="hover:text-indigo-200 transition-colors font-medium">
                      Dashboard
                    </Link>
                    
                    {/* Claims - All roles but different access */}
                    <Link 
                      href={isAdmin || isManager ? "/claims" : "/my-claims"} 
                      className="hover:text-indigo-200 transition-colors font-medium"
                    >
                      {isAdmin || isManager ? 'All Claims' : 'My Claims'}
                    </Link>
                    
                    {/* Employees - Admin only */}
                    {isAdmin && (
                      <Link href="/employees" className="hover:text-indigo-200 transition-colors font-medium">
                        Employees
                      </Link>
                    )}
                    
                    {/* Audit Logs - Admin only */}
                    {isAdmin && (
                      <Link href="/audit-logs" className="hover:text-indigo-200 transition-colors font-medium">
                        📋 Audit Logs
                      </Link>
                    )}
                  </>
                )}

                {/* User info & Logout */}
                <div className="flex items-center gap-3 ml-4 pl-4 border-l border-indigo-400">
                  <span className="text-sm">
                    {user?.name} ({user?.role})
                  </span>
                  <button
                    onClick={logout}
                    className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm transition-colors"
                  >
                    Logout
                  </button>
                </div>
              </nav>
            </div>
          </div>
        </header>
      )}

      {/* Main Content */}
      <main className={isAuthenticated ? "max-w-7xl mx-auto px-4 py-8" : ""}>
        {children}
      </main>
    </div>
  );
}

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
        <AuthProvider>
          <LayoutContent>{children}</LayoutContent>
        </AuthProvider>
      </body>
    </html>
  );
}
