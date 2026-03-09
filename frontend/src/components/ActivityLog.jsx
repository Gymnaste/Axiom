import React, { useEffect, useState } from 'react';
import { portfolioAPI } from '../services/apiService';

export default function ActivityLog() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchLogs = async () => {
        try {
            const res = await portfolioAPI.getActivity();
            setLogs(Array.isArray(res.data) ? res.data : []);
        } catch (error) {
            console.error("Erreur lors de la récupération des logs d'activité:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
        // Rafraîchir toutes les minutes
        const interval = setInterval(fetchLogs, 60000);
        return () => clearInterval(interval);
    }, []);

    const handleLogClick = (log) => {
        if (log.reference_id) {
            // Émettre un événement personnalisé pour le chatbot
            const event = new CustomEvent('open-chat-message', { 
                detail: { messageId: log.reference_id } 
            });
            window.dispatchEvent(event);
        }
    };

    if (loading && logs.length === 0) {
        return <div className="p-4 text-gray-500 text-xs italic">Chargement de l'activité...</div>;
    }

    return (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 flex flex-col h-full overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    <span className="w-2 h-2 bg-sky-500 rounded-full animate-pulse"></span>
                    Activité Autonome Axiom
                </h3>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-2 max-h-[400px]">
                {logs.length === 0 ? (
                    <p className="p-4 text-gray-600 text-xs italic text-center">Aucune activité récente.</p>
                ) : (
                    logs.map((log) => (
                        <div 
                            key={log.id} 
                            onClick={() => handleLogClick(log)}
                            className={`p-3 rounded-lg bg-gray-800/40 border border-gray-700/50 transition-all group ${log.reference_id ? 'cursor-pointer hover:border-sky-500 hover:bg-sky-500/10 active:scale-[0.98]' : 'hover:border-gray-600'}`}
                        >
                            <div className="flex justify-between items-start mb-1">
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${log.type === 'BUY' ? 'bg-green-500/20 text-green-400' :
                                    log.type === 'SELL' ? 'bg-red-500/20 text-red-400' :
                                        'bg-sky-500/20 text-sky-400'
                                    }`}>
                                    {log.type}
                                </span>
                                <span className="text-[9px] text-gray-500 font-mono">
                                    {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                            </div>
                            <p className="text-xs text-gray-300 leading-relaxed">
                                {log.message}
                                {log.reference_id && (
                                    <span className="block mt-1 text-[10px] text-sky-400 font-bold group-hover:underline italic">
                                        Voir l'analyse complète →
                                    </span>
                                )}
                            </p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
