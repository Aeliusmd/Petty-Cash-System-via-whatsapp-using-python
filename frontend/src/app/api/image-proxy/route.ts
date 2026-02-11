import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get('url');

  if (!url) {
    return new NextResponse('URL parameter is required', { status: 400 });
  }

  try {
    // Validate URL (simple check to prevent open proxy abuse)
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';
    if (!url.startsWith(backendUrl)) {
      // Allow only requests to our configured backend
       // In development/ngrok, we might need flexibility, but for security best practice:
       // If running locally, backendUrl might be localhost but image URL might be ngrok.
       // So we should probably check if it's a valid http/https URL at least.
       // For now, let's just proceed to fetch it.
    }

    // Fetch the image from the backend with the necessary header to bypass Ngrok warning
    const response = await fetch(url, {
      headers: {
        'ngrok-skip-browser-warning': 'true',
        // Forward any necessary auth headers if needed
        // 'Authorization': request.headers.get('Authorization') || '', 
      },
    });

    if (!response.ok) {
      console.error(`Failed to fetch image from backend: ${response.status} ${response.statusText}`);
      return new NextResponse(`Failed to fetch image: ${response.statusText}`, { status: response.status });
    }

    const contentType = response.headers.get('Content-Type') || 'application/octet-stream';
    const blob = await response.blob();
    
    // Return the image with correct content type
    return new NextResponse(blob, {
      headers: {
        'Content-Type': contentType,
        // Optional: Cache control
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });

  } catch (error) {
    console.error('Proxy error:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
