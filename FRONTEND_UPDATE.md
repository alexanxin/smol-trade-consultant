# Frontend Update Guide for N8N Integration

## Overview

Update your Next.js frontend to use the n8n webhook instead of the local `/api/analyze` route.

## Current Implementation

Your frontend currently calls the local Next.js API route:

```typescript
// Current code (likely in your page.tsx or a hook)
const response = await fetch("/api/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ token, chain }),
});
```

## Updated Implementation

Replace with n8n webhook URL:

```typescript
// Updated code for n8n integration
const response = await fetch(
  "https://your-n8n-server.com/webhook/trading-analysis",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, chain }),
  }
);
```

## Step-by-Step Update

1. **Find where API calls are made** in your frontend
2. **Update the fetch URL** to point to your n8n webhook
3. **Add error handling** for external requests
4. **Test the integration**

## Code Changes

### Option 1: Direct URL Update

```typescript
// Find this pattern in your code
fetch("/api/analyze", {
  method: "POST",
  body: JSON.stringify({ token, chain }),
});

// Replace with:
fetch("https://your-n8n-server.com/webhook/trading-analysis", {
  method: "POST",
  headers: { "Content-Type": "application/json" }, // Add this header
  body: JSON.stringify({ token, chain }),
});
```

### Option 2: Environment Variable (Recommended)

1. **Add to your `.env.local` or `.env`**:

   ```
   NEXT_PUBLIC_N8N_WEBHOOK_URL=https://your-n8n-server.com/webhook/trading-analysis
   ```

2. **Update the fetch call**:

   ```typescript
   const webhookUrl = process.env.NEXT_PUBLIC_N8N_WEBHOOK_URL;

   fetch(webhookUrl, {
     method: "POST",
     headers: { "Content-Type": "application/json" },
     body: JSON.stringify({ token, chain }),
   });
   ```

### Option 3: Configuration Object

Create a config file for better maintainability:

```typescript
// lib/api-config.ts
export const API_CONFIG = {
  webhookUrl: process.env.NEXT_PUBLIC_N8N_WEBHOOK_URL || "/api/analyze",
  fallbackUrl: "/api/analyze", // Keep local API as fallback
};

// Usage in your component:
import { API_CONFIG } from "@/lib/api-config";

fetch(API_CONFIG.webhookUrl, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ token, chain }),
});
```

## Error Handling Enhancements

Since you're now calling an external API, add better error handling:

```typescript
try {
  const response = await fetch(webhookUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Add timeout if needed
    },
    body: JSON.stringify({ token, chain }),
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data;
} catch (error) {
  console.error("N8N API Error:", error);

  // Optional: Fallback to local API
  return fallbackToLocalAPI(token, chain);
}

async function fallbackToLocalAPI(token: string, chain: string) {
  // Fallback to local API if n8n fails
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, chain }),
  });
  return response.json();
}
```

## Testing

1. **Start your frontend development server**
2. **Test with your n8n webhook URL**
3. **Verify data structure matches** current expectations
4. **Test error scenarios** (network failures, timeouts)

## Environment Setup

### For Development

```bash
# .env.local
NEXT_PUBLIC_N8N_WEBHOOK_URL=http://localhost:5678/webhook/trading-analysis
```

### For Production

```bash
# .env.production
NEXT_PUBLIC_N8N_WEBHOOK_URL=https://your-production-n8n.com/webhook/trading-analysis
```

## CORS Considerations

If you encounter CORS errors, configure n8n to allow your frontend's domain:

1. **In n8n**: Add your frontend domain to allowed CORS origins
2. **Alternative**: Use a proxy on your frontend server to avoid CORS issues

## Fallback Strategy

Consider implementing a fallback system where:

- If n8n webhook fails, automatically fall back to local API
- If both fail, show cached data or offline message
- Log errors for monitoring

## Performance Optimizations

1. **Caching**: Cache responses in localStorage for recent requests
2. **Debouncing**: Prevent rapid-fire requests
3. **Loading States**: Show proper loading indicators
4. **Error Boundaries**: Wrap components in error boundaries

## Migration Strategy

1. **Phase 1**: Keep both APIs functional
2. **Phase 2**: Switch frontend to use n8n webhook
3. **Phase 3**: Test thoroughly
4. **Phase 4**: Remove local API route if no longer needed

This approach ensures zero downtime during the migration.
