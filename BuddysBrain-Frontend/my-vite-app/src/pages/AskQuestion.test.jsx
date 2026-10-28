import React from 'react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import AskQuestion from './AskQuestion';

vi.mock('axios', () => ({ default: { post: vi.fn() } }));

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test');
  vi.stubEnv('VITE_ENABLE_LIVE', 'true');
  vi.stubGlobal('SpeechRecognition', undefined);
  vi.stubGlobal('webkitSpeechRecognition', undefined);
  vi.stubGlobal('speechSynthesis', undefined);
});

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function renderPage() {
  render(<React.StrictMode><MemoryRouter initialEntries={['/ask?mode=live']}><AskQuestion /></MemoryRouter></React.StrictMode>);
  return userEvent.setup();
}

test('typed questions work without speech APIs and display the answer', async () => {
  axios.post.mockResolvedValue({ data: { summary: 'A heap is a tree.', results: [] } });
  const user = renderPage();
  expect(screen.getByRole('button', { name: 'Start recording' }).disabled).toBe(true);
  await user.type(screen.getByLabelText('Your question'), 'What is a heap?{Enter}');
  expect(await screen.findByText('A heap is a tree.')).toBeTruthy();
  expect(axios.post).toHaveBeenCalledWith('https://api.example.test/search', { query: 'What is a heap?' }, { timeout: 90000, signal: expect.any(AbortSignal) });
});

test('an in-flight question cannot be submitted twice', async () => {
  let resolve;
  axios.post.mockReturnValue(new Promise(done => { resolve = done; }));
  const user = renderPage();
  await user.type(screen.getByLabelText('Your question'), 'Explain trees');
  await user.dblClick(screen.getByRole('button', { name: 'Ask Buddy' }));
  expect(axios.post).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Your question').disabled).toBe(true);
  resolve({ data: { summary: 'Tree answer', results: [] } });
  expect(await screen.findByText('Tree answer')).toBeTruthy();
});

test('service errors preserve the question for retry and do not claim no matches', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  axios.post.mockRejectedValue({ response: { data: { detail: 'AI processing timed out. Please try again.' } } });
  const user = renderPage();
  await user.type(screen.getByLabelText('Your question'), 'Explain sorting{Enter}');
  expect(await screen.findByText('AI processing timed out. Please try again.')).toBeTruthy();
  expect(screen.getByLabelText('Your question').value).toBe('Explain sorting');
  expect(screen.queryByText('No internal resources matched this question.')).toBeNull();
});

test('missing API configuration does not request an undefined address', async () => {
  vi.stubEnv('VITE_API_BASE_URL', '');
  vi.spyOn(console, 'error').mockImplementation(() => {});
  renderPage();
  expect(screen.getByText('Demo · saved examples')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Ask live' }).disabled).toBe(true);
  expect(axios.post).not.toHaveBeenCalled();
});
