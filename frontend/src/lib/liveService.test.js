import { afterEach, expect, test, vi } from 'vitest';
import { apiBaseUrl, serviceError, uploadLimitBytes } from './liveService';

afterEach(() => vi.unstubAllEnvs());

test('same-origin API works only when live mode is explicitly enabled', () => {
  vi.stubEnv('VITE_API_BASE_URL', '/api/');
  vi.stubEnv('VITE_ENABLE_LIVE', 'false');
  expect(apiBaseUrl()).toBe('');
  vi.stubEnv('VITE_ENABLE_LIVE', 'true');
  expect(apiBaseUrl()).toBe('/api');
  expect(uploadLimitBytes()).toBe(4_000_000);
});

test.each(['//untrusted.example', '/unexpected', 'javascript:alert(1)', '/api?key=secret'])('rejects invalid API address %s', value => {
  vi.stubEnv('VITE_ENABLE_LIVE', 'true');
  vi.stubEnv('VITE_API_BASE_URL', value);
  expect(apiBaseUrl()).toBe('');
});

test('separately hosted API keeps absolute addressing and existing upload limit', () => {
  vi.stubEnv('VITE_ENABLE_LIVE', 'true');
  vi.stubEnv('VITE_API_BASE_URL', 'https://backend.example/');
  expect(apiBaseUrl()).toBe('https://backend.example');
  expect(uploadLimitBytes()).toBe(10 * 1024 * 1024);
});

test('platform payload rejection gets a useful message without a JSON body', () => {
  expect(serviceError({ response: { status: 413, data: 'FUNCTION_PAYLOAD_TOO_LARGE' } }))
    .toBe('The upload is too large for this deployment. Try a smaller file.');
});
