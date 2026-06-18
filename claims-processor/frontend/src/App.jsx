import React, { useState } from 'react';
import ClaimForm from './components/ClaimForm';
import DecisionView from './components/DecisionView';
import TestRunner from './components/TestRunner';

const navStyle = {
  background: '#1a202c', padding: '0 32px', display: 'flex', alignItems: 'center', gap: 32, height: 56,
};
const navLink = (active, disabled = false) => ({
  color: active ? '#fff' : disabled ? '#4a5568' : '#a0aec0',
  fontWeight: active ? 700 : 500, fontSize: 14,
  cursor: disabled ? 'not-allowed' : 'pointer',
  borderBottom: active ? '2px solid #3182ce' : '2px solid transparent',
  paddingBottom: 2, transition: 'all 0.15s',
  opacity: disabled ? 0.45 : 1,
  position: 'relative',
});

export default function App() {
  const [tab, setTab] = useState('submit');
  const [decision, setDecision] = useState(null);
  const [lastClaimData, setLastClaimData] = useState(null);

  const handleResult = (d, claimPayload) => {
    setDecision(d);
    setLastClaimData(claimPayload);
    setTab('result');
  };

  const handleFixAndResubmit = () => {
    // Keep lastClaimData so ClaimForm pre-fills it, but clear decision
    setDecision(null);
    setTab('submit');
  };

  const handleNewClaim = () => {
    setDecision(null);
    setLastClaimData(null);
    setTab('submit');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      <nav style={navStyle}>
        <span style={{ color: '#fff', fontWeight: 800, fontSize: 16, marginRight: 16 }}>Claims Processor</span>
        <span style={navLink(tab === 'submit')} onClick={handleNewClaim}>Submit Claim</span>
        <span
          style={navLink(tab === 'result', !decision)}
          onClick={() => decision && setTab('result')}
          title={!decision ? 'Submit a claim first to see the decision' : ''}
        >
          Decision {!decision && <span style={{ fontSize: 10, marginLeft: 4 }}>🔒</span>}
        </span>
        <span style={navLink(tab === 'test')} onClick={() => setTab('test')}>Test Runner</span>
      </nav>

      <div style={{ maxWidth: 780, margin: '32px auto', padding: '0 16px' }}>
        {tab === 'submit' && (
          <ClaimForm
            onResult={handleResult}
            initialData={lastClaimData}
            onNewClaim={handleNewClaim}
          />
        )}
        {tab === 'result' && decision && (
          <DecisionView
            decision={decision}
            onBack={handleFixAndResubmit}
            onNewClaim={handleNewClaim}
          />
        )}
        {tab === 'result' && !decision && (
          <div style={{ textAlign: 'center', color: '#718096', marginTop: 60 }}>
            No decision yet. <span style={{ color: '#3182ce', cursor: 'pointer' }} onClick={() => setTab('submit')}>Submit a claim first.</span>
          </div>
        )}
        {tab === 'test' && <TestRunner />}
      </div>
    </div>
  );
}
