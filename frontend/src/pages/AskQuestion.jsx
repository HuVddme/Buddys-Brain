import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import DemoExplorer from './DemoExplorer';
import LiveQuestion from './LiveQuestion';
import { apiBaseUrl } from '../lib/liveService';
import '../styles/AskQuestion.css';
import '../styles/Demo.css';

export default function AskQuestionPage() {
  const [params] = useSearchParams();
  const liveAvailable = Boolean(apiBaseUrl());
  const [mode, setMode] = useState(params.get('mode') === 'live' && liveAvailable ? 'live' : 'demo');
  return (
    <main className="study-page">
      <Link to="/" className="study-back">← Home</Link>
      <header className="study-header">
        <p className="study-eyebrow">BUDDY’S BRAIN · STUDY TOGETHER</p>
        <h1>Ask Buddy the Bison</h1>
        <p>Start with a sample lesson, or ask about your connected course library.</p>
      </header>
      <div className="mode-switch" role="group" aria-label="Choose how to ask Buddy">
        <button aria-pressed={mode === 'demo'} onClick={() => setMode('demo')}>Explore demo</button>
        <button aria-pressed={mode === 'live'} disabled={!liveAvailable} onClick={() => setMode('live')}>Ask live</button>
      </div>
      {!liveAvailable && <p className="live-unavailable">Live questions and uploads are not enabled on this site yet. The demo is ready to explore.</p>}
      {mode === 'demo' ? <DemoExplorer /> : <LiveQuestion />}
    </main>
  );
}
