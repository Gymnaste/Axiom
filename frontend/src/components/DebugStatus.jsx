import React, { useState, useEffect } from 'react';
import { systemAPI } from '../services/apiService';

/**
 * DebugStatus — Composant de diagnostic rapide.
 * Affiche l'état de la connexion au backend.
 */
const DebugStatus = () => {
    const [status, setStatus] = useState('checking');
    const [apiUrl, setApiUrl] = useState('');
    const [error, setError] = useState(null);

    useEffect(() => {
        setApiUrl(import.meta.env.VITE_API_URL || 'http://localhost:8000 (default)');
        
        const checkHealth = async () => {
            try {
                const response = await systemAPI.getHealth();
                if (response.data && response.data.status === 'healthy') {
                    setStatus('online');
                } else {
                    setStatus('issues');
                }
            } catch (err) {
                setStatus('offline');
                setError(err.message);
            }
        };

        checkHealth();
    }, []);

    if (process.env.NODE_ENV !== 'development' && !window.location.search.includes('debug=true')) {
        return null;
    }

    return (
        <div style={{
            position: 'fixed',
            bottom: '10px',
            right: '10px',
            backgroundColor: 'rgba(0,0,0,0.8)',
            color: 'white',
            padding: '10px',
            borderRadius: '5px',
            fontSize: '10px',
            zIndex: 9999,
            border: `1px solid ${status === 'online' ? '#00ff00' : '#ff0000'}`
        }}>
            <div><strong>Axiom Debug</strong></div>
            <div>Status: <span style={{ color: status === 'online' ? '#00ff00' : '#ffaa00' }}>{status.toUpperCase()}</span></div>
            <div>API: {apiUrl}</div>
            {error && <div style={{ color: '#ff5555' }}>Error: {error}</div>}
        </div>
    );
};

export default DebugStatus;
