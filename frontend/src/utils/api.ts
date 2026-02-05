// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

/**
 * Makes an authenticated fetch request and handles 401 errors automatically
 * @param url - The URL to fetch
 * @param options - Fetch options (headers will be merged with auth header)
 * @returns Response object
 */
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('auth_token');
  
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`,
    // Bypass Ngrok browser warning for free tier
    'ngrok-skip-browser-warning': 'true',
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // If we get a 401, the token is invalid - clear auth and redirect to login
  if (response.status === 401) {
    console.error('❌ 401 Unauthorized - Clearing auth and redirecting to login');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('auth_user');
    
    // Redirect to login page
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  return response;
}

/**
 * Helper to get the auth token from localStorage
 */
export function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

/**
 * Helper to check if user is authenticated
 */
export function isAuthenticated(): boolean {
  const token = getAuthToken();
  if (!token) return false;

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000;
    return Date.now() < exp;
  } catch {
    return false;
  }
}


export interface Claim {
  id: number;
  claim_number: string;
  employee_name: string;
  employee_code: string;
  category_name: string;
  category_code: string;
  location_name: string | null;
  status_code: string;
  status_name: string;
  claim_type: string;
  claim_date: string;
  duration_days: number;
  user_amount: number | null;
  system_amount: number | null;
  final_amount: number | null;
  description: string | null;
  rejection_reason: string | null;
  manager_name: string | null;
  approver_name: string | null;
  created_at: string;
  approved_at: string | null;
}

export interface Stats {
  overview: {
    total_claims: number;
    pending_claims: number;
    approved_claims: number;
    rejected_claims: number;
    total_approved_amount: number;
    pending_amount: number;
  };
  categories: Array<{
    category: string;
    category_code: string;
    count: number;
    total_amount: number;
  }>;
  recent_claims: Array<{
    claim_number: string;
    created_at: string;
    employee_name: string;
    category_name: string;
    final_amount: number;
    status_code: string;
  }>;
}

export async function fetchClaims(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ claims: Claim[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  
  const res = await authenticatedFetch(`${API_BASE_URL}/api/claims?${searchParams}`, {
    cache: 'no-store',
  });
  
  if (!res.ok) throw new Error('Failed to fetch claims');
  return res.json();
}

export async function fetchClaim(id: number): Promise<Claim> {
  const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/${id}`, {
    cache: 'no-store',
  });
  if (!res.ok) throw new Error('Failed to fetch claim');
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await authenticatedFetch(`${API_BASE_URL}/api/stats`, {
    cache: 'no-store',
  });
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function approveClaim(id: number): Promise<{ success: boolean; message: string }> {
  const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/${id}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to approve claim');
  }
  return res.json();
}

export async function rejectClaim(id: number, reason: string): Promise<{ success: boolean; message: string }> {
  const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/${id}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to reject claim');
  }
  return res.json();
}
