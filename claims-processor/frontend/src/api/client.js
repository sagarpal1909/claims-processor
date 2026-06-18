import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const submitClaim = (claimData) => api.post('/claims', claimData);
export const getClaim = (claimId) => api.get(`/claims/${claimId}`);
export const listClaims = () => api.get('/claims');
export const runTestCases = () => api.post('/test-run');
