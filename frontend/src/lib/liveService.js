export function apiBaseUrl() {
  const value = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
  if (import.meta.env.VITE_ENABLE_LIVE !== 'true' || !value) return '';
  // Vite runs in the browser: use public same-origin routing, not an internal
  // service binding (which exists only inside server-side functions).
  if (value === '/api') return value;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && !url.search && !url.hash
      ? value : '';
  } catch {
    return '';
  }
}

export function serviceError(error) {
  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return 'The request took too long. Your question or form is still here; try again or explore the demo.';
  }
  if (!error.response) {
    return 'The live backend could not be reached. Check your connection, try again later, or explore the demo.';
  }
  const detail = error.response.data?.detail;
  if (error.response.status === 413) {
    return typeof detail === 'string' ? detail : 'The upload is too large for this deployment. Try a smaller file.';
  }
  if (error.response.status === 429) {
    const seconds = Number(error.response.headers?.['retry-after']);
    const wait = Number.isFinite(seconds) && seconds > 0
      ? ` Try again in about ${Math.ceil(seconds / 60)} minute(s).` : '';
    return (typeof detail === 'string' ? detail : 'The live usage limit has been reached. Explore the demo meanwhile.') + wait;
  }
  if (typeof detail === 'string') return detail;
  if (error.response.status === 422) return 'Please check the submitted fields and try again.';
  if (error.response.status >= 500) return 'The live service could not complete this request. Please try again later or explore the demo.';
  return 'This request could not be completed. Check your input and try again.';
}

export const LIVE_TIMEOUT_MS = 90_000;

export function uploadLimitBytes() {
  // Leave room for multipart form fields beneath Vercel's 4.5 MB body limit.
  return apiBaseUrl() === '/api' ? 4_000_000 : 10 * 1024 * 1024;
}
