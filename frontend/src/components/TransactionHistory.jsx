import React, { useEffect, useState } from 'react';
import { portfolioAPI } from '../services/apiService';

export default function TransactionHistory() {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchTransactions = async () => {
        try {
            const res = await portfolioAPI.getTransactions();
            setTransactions(Array.isArray(res.data) ? res.data : []);
        } catch (error) {
            console.error("Erreur lors de la récupération des transactions:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTransactions();
        const interval = setInterval(fetchTransactions, 30000); // 30s refresh
        return () => clearInterval(interval);
    }, []);

    if (loading && transactions.length === 0) {
        return <div className="p-4 text-gray-500 text-xs italic text-center">Chargement de l'historique...</div>;
    }

    return (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 flex flex-col h-full overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/80">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    <svg className="w-4 h-4 text-sky-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                    </svg>
                    Historique des Achats & Ventes
                </h3>
            </div>

            <div className="flex-1 overflow-y-auto max-h-[500px]">
                <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 bg-gray-900/95 text-[10px] text-gray-500 uppercase font-bold border-b border-gray-800">
                        <tr>
                            <th className="px-4 py-3">Type / Date</th>
                            <th className="px-4 py-3">Symbole</th>
                            <th className="px-4 py-3 text-right">Prix</th>
                            <th className="px-4 py-3 text-right">Qté</th>
                            <th className="px-4 py-3 text-right">Total</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/50">
                        {transactions.length === 0 ? (
                            <tr>
                                <td colSpan="5" className="px-4 py-8 text-center text-gray-600 text-xs italic">
                                    Aucune transaction enregistrée.
                                </td>
                            </tr>
                        ) : (
                            transactions.map((tx) => (
                                <tr key={tx.id} className="hover:bg-white/[0.02] transition-colors group">
                                    <td className="px-4 py-3">
                                        <div className="flex flex-col">
                                            <span className={`text-[10px] font-bold mb-0.5 ${tx.type === 'ACHAT' ? 'text-green-400' : 'text-red-400'}`}>
                                                {tx.type}
                                            </span>
                                            <span className="text-[10px] text-gray-500 font-mono">
                                                {new Date(tx.date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} {new Date(tx.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className="text-xs font-bold text-white group-hover:text-sky-400 transition-colors">
                                            {tx.symbol}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <span className="text-xs text-gray-300 font-mono">
                                            ${tx.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <span className="text-xs text-gray-400">
                                            {tx.quantity.toFixed(4)}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <span className={`text-xs font-bold ${tx.type === 'ACHAT' ? 'text-white' : 'text-sky-400'}`}>
                                            ${tx.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
