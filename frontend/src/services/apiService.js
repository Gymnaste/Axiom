/**
 * apiService.js — Centralise tous les appels API vers le backend FastAPI.
 * Règle frontend : jamais d'appels directs dans les composants.
 */
import axios from 'axios'

const API = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 120000,
})

console.log("Axiom API Service loaded - v1.1 (with getActivity)");
// Cache buster: 2026-03-05 14:26

// Ajouter le token Supabase à chaque requête
API.interceptors.request.use(async (config) => {
    // Récupérer la session depuis le localStorage (géré par Supabase)
    // Supabase v2 utilise souvent le format : sb-<project-id>-auth-token
    const authKey = Object.keys(localStorage).find(key =>
        key.includes('supabase.auth.token') || key.endsWith('-auth-token')
    );

    if (authKey) {
        try {
            const sessionData = JSON.parse(localStorage.getItem(authKey));
            const token = sessionData?.access_token;
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        } catch (e) {
            console.error("Erreur lors de la récupération du token auth:", e);
        }
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

export const portfolioAPI = {
    getSummary: () => API.get('/portfolio'),
    getPositions: () => API.get('/portfolio/positions'),
    getHistory: () => API.get('/portfolio/history'),
    getTradesBySymbol: (symbol) => API.get(`/portfolio/trades/${symbol}`),
    // Trading Manuel
    buy: (symbol, quantity, stopLoss, takeProfit) => API.post('/portfolio/buy', { symbol, quantity, stop_loss: stopLoss, take_profit: takeProfit }),
    sell: (tradeId) => API.post(`/portfolio/sell/${tradeId}`),
    addToPosition: (tradeId, quantity) => API.post(`/portfolio/position/${tradeId}/add`, { quantity }),
    updateTargets: (tradeId, stopLoss, takeProfit) => API.patch(`/portfolio/position/${tradeId}/targets`, { stop_loss: stopLoss, take_profit: takeProfit }),
    withdraw: (amount) => API.post('/portfolio/withdraw', { amount }),
    deposit: (amount) => API.post('/portfolio/deposit', { amount }),
    getActivity: () => API.get('/portfolio/activity'),
    getTransactions: () => API.get('/portfolio/transactions'),
}

export const signalsAPI = {
    getSignals: () => API.get('/signals'),
    runCycle: () => API.post('/run-cycle'),
}

export const newsAPI = {
    getNews: (limit = 20) => API.get(`/news?limit=${limit}`),
    refreshNews: () => API.post('/news/refresh'),
}

export const systemAPI = {
    getHealth: () => API.get('/system/health'),
    getStatus: () => API.get('/system/status'),
}

export const marketAPI = {
    getInfo: (symbol) => API.get(`/market/${symbol}/info`),
    getHistory: (symbol, period = '6mo') => API.get(`/market/${symbol}/history?period=${period}`),
    searchTicker: (query) => API.get(`/market/search-ticker?query=${query}`),
}

export const chatAPI = {
    send: (messages) => API.post('/chat', { messages }),
    getHistory: () => API.get('/chat/history'),
}

export default API
