import React, { useState } from 'react';
import { runTestCases } from '../api';

const STATUS_COLOR = {
  APPROVED: '#38a169', PARTIAL: '#d69e2e', REJECTED: '#e53e3e', MANUAL_REVIEW: '#3182ce',
};

export default function TestRunner() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const run = async () => {
    setLoading(true);
  
    try {
      const res = await runTestCases();
      setResults(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const passed = results?.filter(r => r.passed).length ?? 0;
  const total = results?.length ?? 0;

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 28, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>Test Runner</div>
          <div style={{ fontSize: 13, color: '#718096', marginTop: 4 }}>Run all test cases through the pipeline</div>
        </div>
        <button
          onClick={run} disabled={loading}
          style={{ padding: '10px 24px', background: '#3182ce', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, cursor: 'pointer', fontSize: 14 }}
        >
          {loading ? 'Running…' : 'Run All Tests'}
        </button>
      </div>

      {results && (
        <>
          <div style={{ background: passed === total ? '#f0fff4' : '#fffbeb', borderRadius: 8, padding: '12px 16px', marginBottom: 20, display: 'flex', gap: 24 }}>
            <span style={{ fontWeight: 700, color: '#276749' }}>{passed} passed</span>
            <span style={{ fontWeight: 700, color: '#c53030' }}>{total - passed} failed</span>
            <span style={{ color: '#718096' }}>of {total} total</span>
          </div>

          {results.map((r, i) => (
            <div key={r.case_id} style={{
              border: `1.5px solid ${r.passed ? '#c6f6d5' : '#fed7d7'}`,
              borderRadius: 8, marginBottom: 10, overflow: 'hidden',
            }}>
              <div
                style={{ padding: '12px 16px', background: r.passed ? '#f0fff4' : '#fff5f5', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: r.passed ? '#276749' : '#c53030' }}>
                    {r.passed ? '✓' : '✗'}
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{r.case_id}: {r.case_name}</span>
                  {r.decision?.status && (
                    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: STATUS_COLOR[r.decision.status] || '#718096', color: '#fff', fontWeight: 700 }}>
                      {r.decision.status}
                    </span>
                  )}
                </div>
                <span style={{ fontSize: 11, color: '#718096' }}>{expanded === i ? '▲' : '▼'}</span>
              </div>

              {expanded === i && (
                <div style={{ padding: '14px 16px', fontSize: 13 }}>
                  {r.notes !== 'OK' && (
                    <div style={{ background: '#fffbeb', borderRadius: 6, padding: '8px 12px', marginBottom: 10, color: '#744210' }}>
                      {r.notes}
                    </div>
                  )}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                    <div><span style={{ color: '#718096' }}>Expected: </span><strong>{r.expected_decision || 'REJECTED/STOPPED'}</strong></div>
                    <div><span style={{ color: '#718096' }}>Got: </span><strong>{r.decision?.status}</strong></div>
                    {r.expected_amount && <div><span style={{ color: '#718096' }}>Expected amount: </span><strong>₹{r.expected_amount.toLocaleString('en-IN')}</strong></div>}
                    <div><span style={{ color: '#718096' }}>Approved: </span><strong>₹{r.decision?.approved_amount?.toLocaleString('en-IN')}</strong></div>
                  </div>
                  <div style={{ color: '#4a5568', marginBottom: 8 }}>{r.decision?.message}</div>
                  <details>
                    <summary style={{ cursor: 'pointer', color: '#3182ce', fontWeight: 600, fontSize: 12 }}>View trace ({r.decision?.trace?.length} steps)</summary>
                    <div style={{ marginTop: 8 }}>
                      {r.decision?.trace?.map((step, j) => (
                        <div key={j} style={{ borderLeft: `2px solid ${step.status === 'PASS' ? '#38a169' : step.status === 'FAIL' ? '#e53e3e' : '#d69e2e'}`, paddingLeft: 10, marginBottom: 6 }}>
                          <div style={{ fontSize: 10, color: '#718096', textTransform: 'uppercase' }}>{step.agent} › {step.step}</div>
                          <div style={{ fontSize: 12 }}>{step.detail}</div>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
