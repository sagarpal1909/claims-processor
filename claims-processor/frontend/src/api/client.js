import axios from 'axios';

const API_BASE =
  process.env.REACT_APP_API_URL ||
  'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
});

export const submitClaim = (claimData) => api.post('/claims', claimData);
export const getClaim = (claimId) => api.get(`/claims/${claimId}`);
export const listClaims = () => api.get('/claims');
export const runTestCases = () => api.post('/test-run');