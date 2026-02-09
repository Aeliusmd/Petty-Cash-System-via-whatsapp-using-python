'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { usePathname } from 'next/navigation';

export default function Navigation() {
  const { isAuthenticated, user, logout, exitOrganization, isInOrganization, isSuperAdmin, hasPermission, hasAnyPermission } = useAuth();
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // If not authenticated, don't show navigation
  if (!isAuthenticated) return null;

  // Super admin without org context - show only organizations
  const showOnlyOrganizations = isSuperAdmin && !isInOrganization;

  // Permission-based visibility
  const canViewDashboard = hasAnyPermission(['dashboard.view.org', 'dashboard.view.team']);
  const canViewAllClaims = hasAnyPermission(['claims.read.all', 'claims.read.team', 'claims.approve']);
  const canViewEmployees = hasPermission('employees.read.all');
  const canViewSettings = hasAnyPermission(['config.view', 'config.manage']);
  const canViewAuditLogs = hasPermission('audit.view');
  const canManageRoles = hasPermission('roles.read');
  const canViewClaims = hasAnyPermission(['claims.read.own', 'claims.read.team', 'claims.read.all', 'claims.create']);

  // Determine if the "Settings" parent menu should be visible
  const showSettingsMenu = canViewSettings || canViewEmployees || canManageRoles;

  // Helper to close both menus
  const closeAllMenus = () => {
    setIsMobileMenuOpen(false);
    setIsSettingsOpen(false);
  };

  return (
    <header className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo & Brand */}
          <Link href={showOnlyOrganizations ? "/organizations" : "/"} className="flex items-center gap-3 z-50">
             <span className="text-2xl">💰</span>
             <h1 className="text-xl font-bold truncate">Petty Cash System</h1>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-6">
            
            {showOnlyOrganizations ? (
              <Link href="/organizations" className={`hover:text-indigo-200 transition-colors font-medium ${pathname === '/organizations' ? 'text-white border-b-2 border-white' : 'text-indigo-100'}`}>
                🏢 Organizations
              </Link>
            ) : (
              <>
                {/* Organization Context Indicator */}
                {isInOrganization && (
                  <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-lg mr-2">
                    <span className="text-sm font-semibold truncate max-w-[150px]">📍 {user?.organization_name}</span>
                    {isSuperAdmin && (
                      <button
                        onClick={exitOrganization}
                        className="text-xs bg-red-500/80 hover:bg-red-600 px-2 py-0.5 rounded transition-colors"
                      >
                        Exit
                      </button>
                    )}
                  </div>
                )}

                {canViewDashboard && (
                  <Link href="/" className="hover:text-indigo-200 transition-colors font-medium">Dashboard</Link>
                )}
                
                {canViewClaims && (
                  <Link 
                    href={canViewAllClaims ? "/claims" : "/my-claims"} 
                    className="hover:text-indigo-200 transition-colors font-medium"
                  >
                    {canViewAllClaims ? 'All Claims' : 'My Claims'}
                  </Link>
                )}
                
                {canViewAuditLogs && (
                  <Link href="/audit-logs" className="hover:text-indigo-200 transition-colors font-medium">Audit Logs</Link>
                )}

                {/* Settings Dropdown */}
                {showSettingsMenu && (
                  <div className="relative group">
                    <button 
                      className="flex items-center gap-1 hover:text-indigo-200 transition-colors font-medium focus:outline-none"
                    >
                      Settings
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 opacity-70 group-hover:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    
                    <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl overflow-hidden py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 transform origin-top-right z-50">
                       {canViewSettings && (
                         <Link href="/settings" className="block px-4 py-2 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-600 transition-colors">
                           Departments & Categories
                         </Link>
                       )}
                       {canViewEmployees && (
                         <Link href="/employees" className="block px-4 py-2 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-600 transition-colors">
                           Employees
                         </Link>
                       )}
                       {canManageRoles && (
                         <Link href="/roles" className="block px-4 py-2 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-600 transition-colors">
                           Roles
                         </Link>
                       )}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* User Profile & Logout (Desktop) */}
            <div className="flex items-center gap-3 ml-4 pl-4 border-l border-indigo-400">
              <div className="flex flex-col items-end">
                <span className="text-sm font-semibold">{user?.name}</span>
                <span className="text-xs text-indigo-200">{user?.role}</span>
              </div>
              <button
                onClick={logout}
                className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm transition-colors"
              >
                Logout
              </button>
            </div>
          </nav>

          {/* Mobile Hamburger Button */}
          <button 
            className="lg:hidden z-50 p-2 focus:outline-none" 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle menu"
          >
            <div className={`w-6 h-0.5 bg-white mb-1.5 transition-all ${isMobileMenuOpen ? 'rotate-45 translate-y-2' : ''}`}></div>
            <div className={`w-6 h-0.5 bg-white mb-1.5 transition-all ${isMobileMenuOpen ? 'opacity-0' : ''}`}></div>
            <div className={`w-6 h-0.5 bg-white transition-all ${isMobileMenuOpen ? '-rotate-45 -translate-y-2' : ''}`}></div>
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      <div 
        className={`fixed inset-0 bg-indigo-900/95 backdrop-blur-sm z-40 transition-transform duration-300 lg:hidden flex flex-col pt-24 px-6 gap-6 ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Mobile User Info */}
        <div className="flex items-center gap-4 pb-6 border-b border-indigo-700">
           <div className="w-12 h-12 bg-indigo-500 rounded-full flex items-center justify-center text-xl font-bold">
              {user?.name?.charAt(0).toUpperCase()}
           </div>
           <div>
              <p className="font-bold text-lg">{user?.name}</p>
              <p className="text-indigo-300 text-sm">{user?.role}</p>
           </div>
        </div>

        {/* Mobile Links */}
        <div className="flex flex-col gap-4 text-lg overflow-y-auto max-h-[60vh]">
           {showOnlyOrganizations ? (
              <Link href="/organizations" onClick={closeAllMenus} className="py-2 border-b border-indigo-800">🏢 Organizations</Link>
            ) : (
              <>
                {isInOrganization && (
                  <div className="flex items-center justify-between py-2 border-b border-indigo-800 bg-indigo-800/50 px-3 rounded-lg">
                    <span className="text-sm font-semibold">📍 {user?.organization_name}</span>
                    {isSuperAdmin && (
                      <button onClick={() => { closeAllMenus(); exitOrganization(); }} className="text-xs bg-red-500 px-2 py-1 rounded">
                        Exit
                      </button>
                    )}
                  </div>
                )}

                {canViewDashboard && (
                  <Link href="/" onClick={closeAllMenus} className="py-2 border-b border-indigo-800">Dashboard</Link>
                )}
                
                {canViewClaims && (
                  <Link href={canViewAllClaims ? "/claims" : "/my-claims"} onClick={closeAllMenus} className="py-2 border-b border-indigo-800">
                    {canViewAllClaims ? 'All Claims' : 'My Claims'}
                  </Link>
                )}
                
                {canViewAuditLogs && (
                   <Link href="/audit-logs" onClick={closeAllMenus} className="py-2 border-b border-indigo-800">Audit Logs</Link>
                )}

                {/* Mobile Settings Group */}
                {showSettingsMenu && (
                  <div className="border-b border-indigo-800 pb-2">
                    <button 
                      onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                      className="flex items-center justify-between w-full py-2 font-medium"
                    >
                      <span className="flex items-center gap-2">Settings</span>
                      <svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 transition-transform ${isSettingsOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    
                    <div className={`overflow-hidden transition-all duration-300 ${isSettingsOpen ? 'max-h-48 opacity-100 mt-2' : 'max-h-0 opacity-0'}`}>
                      <div className="flex flex-col gap-3 pl-6 text-base text-indigo-200">
                        {canViewSettings && (
                           <Link href="/settings" onClick={closeAllMenus} className="block hover:text-white transition-colors">Departments & Categories</Link>
                        )}
                        {canViewEmployees && (
                           <Link href="/employees" onClick={closeAllMenus} className="block hover:text-white transition-colors">Employees</Link>
                        )}
                        {canManageRoles && (
                           <Link href="/roles" onClick={closeAllMenus} className="block hover:text-white transition-colors">Roles</Link>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
        </div>

        <button 
          onClick={logout} 
          className="mt-auto mb-8 w-full py-3 bg-red-500/80 hover:bg-red-600 rounded-xl font-bold transition-colors"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
