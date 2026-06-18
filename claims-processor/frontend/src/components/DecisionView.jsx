import React, { useState } from 'react';

const STATUS_COLORS = {
  APPROVED: { bg: '#f0fff4', border: '#68d391', text: '#276749', badge: '#38a169' },
  PARTIAL:  { bg: '#fffbeb', border: '#f6e05e', text: '#744210', badge: '#d69e2e' },
  REJECTED: { bg: '#fff5f5', border: '#feb2b2', text: '#742a2a', badge: '#e53e3e' },
  MANUAL_REVIEW: { bg: '#ebf8ff', border: '#90cdf4', text: '#1a365d', badge: '#3182ce' },
};

const STEP_COLORS = {
  PASS: '#38a169', FAIL: '#e53e3e', WARN: '#d69e2e', INFO: '#3182ce', ERROR: '#e53e3e',
};

const s = {
  card: { background: '#fff', borderRadius: 12, padding: 28, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', marginBottom: 20 },
  statusBadge: (status) => ({
    display: 'inline-block', padding: '6px 16px', borderRadius: 20,
    background: STATUS_COLORS[status]?.badge || '#718096', color: '#fff', fontWeight: 700, fontSize: 14,
  }),
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 },
  amount: { fontSize: 28, fontWeight: 800, color: '#1a202c' },
  label: { fontSize: 12, color: '#718096', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 600 },
  sectionTitle: { fontSize: 15, fontWeight: 700, color: '#2d3748', marginBottom: 12, marginTop: 20 },
  traceItem: (status) => ({
    borderLeft: `3px solid ${STEP_COLORS[status] || '#718096'}`,
    paddingLeft: 12, paddingTop: 6, paddingBottom: 6, marginBottom: 8,
    background: '#f9fafb', borderRadius: '0 6px 6px 0',
  }),
  traceAgent: { fontSize: 11, color: '#718096', fontWeight: 600, textTransform: 'uppercase' },
  traceDetail: { fontSize: 13, color: '#2d3748', marginTop: 2 },
  lineItem: (status) => ({
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '10px 14px', borderRadius: 8, marginBottom: 6,
    background: status === 'APPROVED' ? '#f0fff4' : '#fff5f5',
    border: `1px solid ${status === 'APPROVED' ? '#c6f6d5' : '#fed7d7'}`,
  }),
  confidenceBar: (score) => ({
    height: 8, borderRadius: 4,
    background: score > 0.8 ? '#38a169' : score > 0.5 ? '#d69e2e' : '#e53e3e',
    width: `${score * 100}%`, transition: 'width 0.5s',
  }),
  toggleBtn: { background: 'none', border: 'none', color: '#3182ce', cursor: 'pointer', fontSize: 13, fontWeight: 600, padding: 0 },
  backBtn: { padding: '10px 20px', background: '#edf2f7', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  failureAlert: { background: '#fffbeb', border: '1px solid #f6e05e', borderRadius: 8, padding: '10px 14px', marginBottom: 12, fontSize: 13, color: '#744210' },
  resubmitBanner: {
    background: '#fff5f5', border: '1.5px solid #feb2b2', borderRadius: 12,
    padding: '20px 24px', marginBottom: 20,
  },
  resubmitBtn: {
    display: 'inline-block', marginTop: 12, padding: '10px 22px',
    background: '#3182ce', color: '#fff', border: 'none', borderRadius: 8,
    cursor: 'pointer', fontWeight: 700, fontSize: 14,
  },
};

const DOC_REJECTION_REASONS = ['UNREADABLE_DOCUMENT', 'WRONG_DOCUMENT_TYPE', 'CROSS_PATIENT_MISMATCH'];

const DOC_FIX_MESSAGES = {
  UNREADABLE_DOCUMENT: {
    title: 'A document could not be read',
    instruction: 'Please go back, re-upload a clear, well-lit photo of the document marked as unreadable, and resubmit your claim.',
  },
  WRONG_DOCUMENT_TYPE: {
    title: 'Wrong document type uploaded',
    instruction: 'Please go back, replace the incorrect document with the required one, and resubmit your claim.',
  },
  CROSS_PATIENT_MISMATCH: {
    title: 'Documents belong to different patients',
    instruction: 'Please go back and ensure all uploaded documents are for the same patient, then resubmit.',
  },
};

export default function DecisionView({ decision, onBack, onNewClaim }) {
  const [showTrace, setShowTrace] = useState(false);
  const colors = STATUS_COLORS[decision.status] || STATUS_COLORS.REJECTED;

  const docRejection = decision.rejection_reasons?.find(r => DOC_REJECTION_REASONS.includes(r));
  const fixInfo = docRejection ? DOC_FIX_MESSAGES[docRejection] : null;

  return (
    <div>
      {/* Header card */}
      <div style={{ ...s.card, background: colors.bg, border: `1.5px solid ${colors.border}` }}>
        <div style={s.row}>
          <div>
            <div style={s.label}>Decision</div>
            <div style={{ marginTop: 6 }}>
              <span style={s.statusBadge(decision.status)}>{decision.status}</span>
            </div>
            {!fixInfo && (
            <div style={{ marginTop: 16, fontSize: 13, color: colors.text, maxWidth: 500 }}>{decision.message}</div>
          )}
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={s.label}>Approved Amount</div>
            <div style={s.amount}>₹{decision.approved_amount.toLocaleString('en-IN')}</div>
            <div style={{ fontSize: 12, color: '#718096', marginTop: 4 }}>
              of ₹{decision.claimed_amount.toLocaleString('en-IN')} claimed
            </div>
          </div>
        </div>
      </div>

      {/* Document fix banner */}
      {fixInfo && (
        <div style={s.resubmitBanner}>
          <div style={{ fontWeight: 700, fontSize: 15, color: '#742a2a', marginBottom: 6 }}>
            ⚠️ {fixInfo.title}
          </div>
          <div style={{ fontSize: 13, color: '#742a2a', lineHeight: 1.6 }}>
            {decision.message}
          </div>
          <div style={{ fontSize: 13, color: '#4a5568', marginTop: 10, lineHeight: 1.6 }}>
            {fixInfo.instruction}
          </div>
          <button style={s.resubmitBtn} onClick={onBack}>
            ↑ Fix Documents & Resubmit
          </button>
        </div>
      )}

      {/* Component failures */}
      {decision.component_failures?.length > 0 && (
        <div style={s.failureAlert}>
          ⚠️ <strong>Pipeline ran with degraded components:</strong>{' '}
          {decision.component_failures.join(', ')}. Manual review recommended.
        </div>
      )}

      {/* Fraud signals */}
      {decision.fraud_signals?.length > 0 && (
        <div style={{ ...s.failureAlert, background: '#fff5f5', border: '1px solid #fed7d7', color: '#742a2a' }}>
          🚨 <strong>Fraud signals:</strong> {decision.fraud_signals.join(' | ')}
        </div>
      )}

      {/* Confidence */}
      <div style={s.card}>
        <div style={s.label}>Confidence Score</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
          <div style={{ flex: 1, background: '#edf2f7', borderRadius: 4, height: 8 }}>
            <div style={s.confidenceBar(decision.confidence_score)} />
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, minWidth: 40 }}>
            {(decision.confidence_score * 100).toFixed(0)}%
          </span>
        </div>
        <div style={{ fontSize: 12, color: '#718096', marginTop: 6 }}>
          Claim ID: {decision.claim_id}
        </div>
      </div>

      {/* Financial breakdown */}
      {decision.financial_breakdown && (
        <div style={s.card}>
          <div style={s.sectionTitle}>Financial Breakdown</div>
          {Object.entries(decision.financial_breakdown).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f0f0f0', fontSize: 13 }}>
              <span style={{ color: '#718096', textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</span>
              <span style={{ fontWeight: 600 }}>{typeof v === 'number' ? `₹${v.toLocaleString('en-IN')}` : `${v}%`}</span>
            </div>
          ))}
        </div>
      )}

      {/* Line items */}
      {decision.line_items?.length > 0 && (
        <div style={s.card}>
          <div style={s.sectionTitle}>Line Item Decisions</div>
          {decision.line_items.map((li, i) => (
            <div key={i} style={s.lineItem(li.status)}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{li.description}</div>
                {li.reason && <div style={{ fontSize: 12, color: '#718096', marginTop: 2 }}>{li.reason}</div>}
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 700, color: li.status === 'APPROVED' ? '#276749' : '#e53e3e' }}>
                  ₹{li.approved_amount.toLocaleString('en-IN')}
                </div>
                <div style={{ fontSize: 11, color: '#718096' }}>of ₹{li.claimed_amount.toLocaleString('en-IN')}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Rejection reasons */}
      {decision.rejection_reasons?.length > 0 && (
        <div style={s.card}>
          <div style={s.sectionTitle}>Rejection Reasons</div>
          {decision.rejection_reasons.map((r, i) => (
            <div key={i} style={{ padding: '8px 12px', background: '#fff5f5', borderRadius: 6, marginBottom: 6, fontSize: 13, color: '#742a2a', fontWeight: 600 }}>
              {r.replace(/_/g, ' ')}
            </div>
          ))}
        </div>
      )}

      {/* Trace */}
      <div style={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={s.sectionTitle}>Decision Trace ({decision.trace?.length} steps)</div>
          <button style={s.toggleBtn} onClick={() => setShowTrace(v => !v)}>
            {showTrace ? 'Hide trace ▲' : 'Show trace ▼'}
          </button>
        </div>
        {showTrace && (
          <div style={{ marginTop: 8 }}>
            {decision.trace?.map((step, i) => (
              <div key={i} style={s.traceItem(step.status)}>
                <div style={s.traceAgent}>{step.agent} › {step.step}</div>
                <div style={s.traceDetail}>{step.detail}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        {onNewClaim && <button style={s.backBtn} onClick={onNewClaim}>+ New Claim</button>}
        {!fixInfo && <button style={s.backBtn} onClick={onBack}>← Submit another claim</button>}
      </div>
    </div>
  );
}
