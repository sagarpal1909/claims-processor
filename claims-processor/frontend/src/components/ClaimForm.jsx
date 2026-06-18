import React, { useState } from 'react';
import { submitClaim } from '../api/client';

const CATEGORIES = ['CONSULTATION', 'DIAGNOSTIC', 'PHARMACY', 'DENTAL', 'VISION', 'ALTERNATIVE_MEDICINE'];
const DOC_TYPES = ['PRESCRIPTION', 'HOSPITAL_BILL', 'PHARMACY_BILL', 'LAB_REPORT', 'DIAGNOSTIC_REPORT', 'DISCHARGE_SUMMARY', 'DENTAL_REPORT'];

const styles = {
  form: { background: '#fff', borderRadius: 12, padding: 32, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', maxWidth: 680 },
  title: { fontSize: 22, fontWeight: 700, color: '#1a202c', marginBottom: 24 },
  section: { marginBottom: 24 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#4a5568', marginBottom: 6 },
  input: { width: '100%', padding: '10px 14px', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 14, outline: 'none' },
  select: { width: '100%', padding: '10px 14px', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 14, background: '#fff' },
  row: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  docCard: { border: '1.5px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 12, background: '#f9fafb' },
  addBtn: { padding: '8px 16px', background: '#ebf4ff', color: '#3182ce', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  removeBtn: { padding: '4px 10px', background: '#fff5f5', color: '#e53e3e', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 },
  submitBtn: { width: '100%', padding: '14px', background: '#3182ce', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 700, cursor: 'pointer', marginTop: 8 },
  error: { background: '#fff5f5', border: '1px solid #feb2b2', borderRadius: 8, padding: '12px 16px', color: '#c53030', fontSize: 13, marginBottom: 16 },
  uploadBox: {
    border: '2px dashed #cbd5e0', borderRadius: 8, padding: '16px 12px', textAlign: 'center',
    cursor: 'pointer', background: '#f7fafc', transition: 'border-color 0.2s',
  },
  uploadBoxActive: {
    border: '2px dashed #3182ce', background: '#ebf8ff',
  },
  filePreview: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
    background: '#f0fff4', border: '1px solid #c6f6d5', borderRadius: 8, marginTop: 8,
  },
};

export default function ClaimForm({ onResult, initialData, onNewClaim }) {
  const [form, setForm] = useState(() => initialData ? {
    member_id: initialData.member_id || 'EMP001',
    policy_id: initialData.policy_id || 'PLUM_GHI_2024',
    claim_category: initialData.claim_category || 'CONSULTATION',
    treatment_date: initialData.treatment_date || new Date().toISOString().split('T')[0],
    submission_date: initialData.submission_date || new Date().toISOString().split('T')[0],
    claimed_amount: String(initialData.claimed_amount || ''),
    hospital_name: initialData.hospital_name || '',
    ytd_claims_amount: String(initialData.ytd_claims_amount || '0'),
  } : {
    member_id: 'EMP001',
    policy_id: 'PLUM_GHI_2024',
    claim_category: 'CONSULTATION',
    treatment_date: new Date().toISOString().split('T')[0],
    submission_date: new Date().toISOString().split('T')[0],
    claimed_amount: '',
    hospital_name: '',
    ytd_claims_amount: '0',
  });

  const [documents, setDocuments] = useState(() => initialData?.documents?.length ? initialData.documents.map(d => ({
    file_id: d.file_id || `F${Date.now()}`,
    file_name: d.file_name || '',
    actual_type: d.actual_type || 'PRESCRIPTION',
    quality: d.quality || 'GOOD',
    file_data: d.file_data || null,
    file_media_type: d.file_media_type || null,
  })) : [
    { file_id: 'F001', file_name: '', actual_type: 'PRESCRIPTION', quality: 'GOOD', file_data: null, file_media_type: null },
    { file_id: 'F002', file_name: '', actual_type: 'HOSPITAL_BILL', quality: 'GOOD', file_data: null, file_media_type: null },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const updateDoc = (idx, field, value) => {
    setDocuments(docs => docs.map((d, i) => i === idx ? { ...d, [field]: value } : d));
  };

  const addDoc = () => {
    setDocuments(docs => [...docs, { file_id: `F${Date.now()}`, file_name: '', actual_type: 'PRESCRIPTION', quality: 'GOOD', file_data: null, file_media_type: null }]);
  };

  const handleFileUpload = (idx, file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target.result.split(',')[1];
      setDocuments(docs => docs.map((d, i) => i === idx ? {
        ...d,
        file_name: file.name,
        file_data: base64,
        file_media_type: file.type || 'image/jpeg',
      } : d));
    };
    reader.readAsDataURL(file);
  };

  const clearFile = (idx) => {
    setDocuments(docs => docs.map((d, i) => i === idx ? { ...d, file_name: '', file_data: null, file_media_type: null } : d));
  };

  const removeDoc = (idx) => {
    setDocuments(docs => docs.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = {
        ...form,
        claimed_amount: parseFloat(form.claimed_amount),
        ytd_claims_amount: parseFloat(form.ytd_claims_amount || 0),
        documents: documents.map(({ file_id, file_name, actual_type, quality, file_data, file_media_type }) => ({
          file_id, file_name, actual_type, quality,
          ...(file_data ? { file_data, file_media_type } : {}),
        })),
      };
      const res = await submitClaim(payload);
      onResult(res.data, payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.form}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div style={styles.title}>
          {initialData ? 'Fix & Resubmit Claim' : 'Submit a Claim'}
        </div>
        {initialData && onNewClaim && (
          <button type="button" onClick={onNewClaim}
            style={{ background: 'none', border: '1.5px solid #e2e8f0', borderRadius: 8, padding: '6px 14px', fontSize: 13, color: '#718096', cursor: 'pointer' }}>
            + New Claim
          </button>
        )}
      </div>
      {initialData && (
        <div style={{ background: '#ebf8ff', border: '1px solid #90cdf4', borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 13, color: '#2c5282' }}>
          ℹ️ Your previous claim details are pre-filled. Fix the document issue and resubmit.
        </div>
      )}
      {error && <div style={styles.error}>{error}</div>}
      <form onSubmit={handleSubmit}>
        <div style={styles.row}>
          <div style={styles.section}>
            <label style={styles.label}>Member ID</label>
            <input style={styles.input} value={form.member_id} onChange={e => setForm(f => ({ ...f, member_id: e.target.value }))} required />
          </div>
          <div style={styles.section}>
            <label style={styles.label}>Policy ID</label>
            <input style={styles.input} value={form.policy_id} onChange={e => setForm(f => ({ ...f, policy_id: e.target.value }))} required />
          </div>
        </div>
        <div style={styles.row}>
          <div style={styles.section}>
            <label style={styles.label}>Claim Category</label>
            <select style={styles.select} value={form.claim_category} onChange={e => setForm(f => ({ ...f, claim_category: e.target.value }))}>
              {CATEGORIES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div style={styles.section}>
            <label style={styles.label}>Treatment Date</label>
            <input style={styles.input} type="date" value={form.treatment_date} onChange={e => setForm(f => ({ ...f, treatment_date: e.target.value }))} required />
          </div>
        </div>
        <div style={styles.row}>
          <div style={styles.section}>
            <label style={styles.label}>Submission Date</label>
            <input style={styles.input} type="date" value={form.submission_date} onChange={e => setForm(f => ({ ...f, submission_date: e.target.value }))} required />
          </div>
        </div>
        <div style={styles.row}>
          <div style={styles.section}>
            <label style={styles.label}>Claimed Amount (₹)</label>
            <input style={styles.input} type="number" min="0" value={form.claimed_amount} onChange={e => setForm(f => ({ ...f, claimed_amount: e.target.value }))} required />
          </div>
          <div style={styles.section}>
            <label style={styles.label}>Hospital Name (optional)</label>
            <input style={styles.input} value={form.hospital_name} onChange={e => setForm(f => ({ ...f, hospital_name: e.target.value }))} placeholder="e.g. Apollo Hospitals" />
          </div>
        </div>
        <div style={styles.section}>
          <label style={styles.label}>Year-to-Date Claims (₹)</label>
          <input style={styles.input} type="number" min="0" value={form.ytd_claims_amount} onChange={e => setForm(f => ({ ...f, ytd_claims_amount: e.target.value }))} />
        </div>

        <div style={{ ...styles.section, marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <label style={{ ...styles.label, marginBottom: 0 }}>Documents</label>
            <button type="button" style={styles.addBtn} onClick={addDoc}>+ Add Document</button>
          </div>
          {documents.map((doc, idx) => (
            <div key={doc.file_id} style={styles.docCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#2d3748' }}>Document {idx + 1}</span>
                <button type="button" style={styles.removeBtn} onClick={() => removeDoc(idx)}>Remove</button>
              </div>
              <div style={styles.row}>
                <div>
                  <label style={styles.label}>Document Type</label>
                  <select style={styles.select} value={doc.actual_type} onChange={e => updateDoc(idx, 'actual_type', e.target.value)}>
                    {DOC_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label style={styles.label}>Quality</label>
                  <select style={styles.select} value={doc.quality} onChange={e => updateDoc(idx, 'quality', e.target.value)}>
                    <option>GOOD</option>
                    <option>POOR</option>
                    <option>UNREADABLE</option>
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <span style={styles.label}>Upload File (optional)</span>
                <input
                  id={`file-input-${doc.file_id}`}
                  type="file"
                  accept="image/*,.pdf"
                  style={{ display: 'none' }}
                  onChange={e => handleFileUpload(idx, e.target.files[0])}
                />
                {doc.file_data ? (
                  <div style={styles.filePreview}>
                    <span style={{ fontSize: 18 }}>📄</span>
                    <span style={{ flex: 1, fontSize: 13, color: '#276749', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {doc.file_name}
                    </span>
                    <button type="button" onClick={() => clearFile(idx)}
                      style={{ background: 'none', border: 'none', color: '#e53e3e', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>
                      ×
                    </button>
                  </div>
                ) : (
                  <div
                    style={styles.uploadBox}
                    onClick={() => document.getElementById(`file-input-${doc.file_id}`).click()}
                    onDragOver={e => e.preventDefault()}
                    onDrop={e => { e.preventDefault(); handleFileUpload(idx, e.dataTransfer.files[0]); }}
                  >
                    <div style={{ fontSize: 24, marginBottom: 6 }}>📎</div>
                    <div style={{ fontSize: 13, color: '#4a5568', fontWeight: 600 }}>Click to upload or drag & drop</div>
                    <div style={{ fontSize: 11, color: '#a0aec0', marginTop: 4 }}>JPG, PNG, PDF supported</div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <button type="submit" style={styles.submitBtn} disabled={loading}>
          {loading ? 'Processing…' : 'Submit Claim'}
        </button>
      </form>
    </div>
  );
}
