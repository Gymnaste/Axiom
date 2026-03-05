import { useState, useEffect } from 'react'
import { Line } from 'react-chartjs-2'
import {
    Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler
} from 'chart.js'
import { marketAPI, portfolioAPI } from '../services/apiService'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

export default function StockDetailsModal({ symbol, onClose }) {
    const [info, setInfo] = useState(null)
    const [history, setHistory] = useState([])
    const [userTrades, setUserTrades] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    // États pour les actions manuelles
    const [editingTargets, setEditingTargets] = useState(false)
    const [newSL, setNewSL] = useState('')
    const [newTP, setNewTP] = useState('')
    const [actionLoading, setActionLoading] = useState(false)
    const [actionMsg, setActionMsg] = useState(null)
    const [addQty, setAddQty] = useState('')
    const [showAddForm, setShowAddForm] = useState(false)
    const [buyQty, setBuyQty] = useState('10')
    const [buySL, setBuySL] = useState('')
    const [buyTP, setBuyTP] = useState('')

    const fetchData = async () => {
        setLoading(true)
        setError(null)
        try {
            const results = await Promise.allSettled([
                marketAPI.getInfo(symbol),
                marketAPI.getHistory(symbol),
                portfolioAPI.getTradesBySymbol(symbol)
            ])
            if (results[0].status === 'fulfilled') setInfo(results[0].value.data)
            if (results[1].status === 'fulfilled') setHistory(results[1].value.data.history || [])
            if (results[2].status === 'fulfilled') setUserTrades(results[2].value.data || [])
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (!symbol) return
        fetchData()
    }, [symbol])

    if (!symbol) return null

    const sortedHistory = [...history].sort((a, b) => new Date(a.date) - new Date(b.date))
    const openTrade = userTrades.find(t => t.status === 'OPEN')

    const showMsg = (msg, isError = false) => {
        setActionMsg({ text: msg, error: isError })
        setTimeout(() => setActionMsg(null), 4000)
    }

    const handleBuy = async () => {
        if (!buyQty || parseFloat(buyQty) <= 0) return showMsg('Quantité invalide', true)
        setActionLoading(true)
        try {
            const res = await portfolioAPI.buy(
                symbol,
                parseFloat(buyQty),
                buySL ? parseFloat(buySL) : null,
                buyTP ? parseFloat(buyTP) : null
            )
            if (res.data.success) {
                showMsg(`✅ Acheté ${res.data.quantity} unités pour $${res.data.cost?.toFixed(2)}`)
                fetchData()
            } else {
                showMsg(res.data.error, true)
            }
        } catch (e) {
            showMsg(e.response?.data?.detail || 'Erreur réseau', true)
        }
        setActionLoading(false)
    }

    const handleSell = async () => {
        if (!openTrade) return
        if (!confirm(`Vendre ${openTrade.quantity} unités de ${symbol} au prix actuel ?`)) return
        setActionLoading(true)
        try {
            const res = await portfolioAPI.sell(openTrade.id)
            if (res.data.success) {
                const pnl = res.data.pnl
                showMsg(`✅ Vendu @ $${res.data.exit_price?.toFixed(2)} — PnL: ${pnl >= 0 ? '+' : ''}$${pnl?.toFixed(2)}`)
                fetchData()
            } else {
                showMsg(res.data.error, true)
            }
        } catch (e) { showMsg(e.response?.data?.detail || 'Erreur réseau', true) }
        setActionLoading(false)
    }

    const handleAddToPosition = async () => {
        setActionLoading(true)
        try {
            const res = await portfolioAPI.addToPosition(openTrade.id, addQty ? parseFloat(addQty) : null)
            if (res.data.success) {
                showMsg(`✅ +${res.data.added_quantity} unités ajoutées @ $${res.data.at_price?.toFixed(2)}`)
                setShowAddForm(false)
                setAddQty('')
                fetchData()
            } else {
                showMsg(res.data.error, true)
            }
        } catch (e) { showMsg(e.response?.data?.detail || 'Erreur réseau', true) }
        setActionLoading(false)
    }

    const handleUpdateTargets = async () => {
        setActionLoading(true)
        try {
            const res = await portfolioAPI.updateTargets(
                openTrade.id,
                newSL ? parseFloat(newSL) : null,
                newTP ? parseFloat(newTP) : null
            )
            if (res.data.success) {
                showMsg(`✅ Cibles mises à jour — SL: $${res.data.stop_loss?.toFixed(2)}, TP: $${res.data.take_profit?.toFixed(2)}`)
                setEditingTargets(false)
                fetchData()
            } else {
                showMsg(res.data.error, true)
            }
        } catch (e) { showMsg(e.response?.data?.detail || 'Erreur réseau', true) }
        setActionLoading(false)
    }

    const currentPrice = sortedHistory.length > 0 ? sortedHistory[sortedHistory.length - 1].close : null
    const chartData = {
        labels: sortedHistory.map(d => d.date),
        datasets: [{
            label: `Prix de ${symbol} ($)`,
            data: sortedHistory.map(d => d.close),
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            tension: 0.1,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 5
        }]
    }
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', maxTicksLimit: 8 } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } }
        }
    }

    return (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[200] p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-fade-in">

                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-800">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                            {info ? info.name : symbol}
                            <span className="text-sm px-2 py-1 bg-gray-800 text-sky-400 rounded-md">{symbol}</span>
                        </h2>
                        {info && <p className="text-sm text-gray-400 mt-1">{info.sector} &bull; {info.industry}</p>}
                    </div>
                    <button onClick={onClose} className="w-10 h-10 rounded-full bg-gray-800 hover:bg-gray-700 flex items-center justify-center text-gray-400 hover:text-white transition-colors">✕</button>
                </div>

                {/* Corps */}
                <div className="p-6 flex-1 overflow-y-auto">
                    {loading ? (
                        <div className="flex justify-center flex-col items-center py-20">
                            <div className="w-12 h-12 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin" />
                            <p className="mt-4 text-gray-400">Chargement...</p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Message d'action */}
                            {actionMsg && (
                                <div className={`rounded-lg p-3 text-sm border ${actionMsg.error ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-green-500/10 border-green-500/30 text-green-400'}`}>
                                    {actionMsg.text}
                                </div>
                            )}

                            {/* Prix actuel + Position */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                                    <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-1">Prix Actuel</p>
                                    <p className="text-2xl font-bold text-white">${currentPrice?.toFixed(2) || '--'}</p>
                                </div>

                                {openTrade ? (
                                    <div className="md:col-span-2 bg-sky-500/10 border border-sky-500/30 rounded-xl p-4">
                                        <div className="flex flex-wrap gap-4 justify-between items-center">
                                            <div>
                                                <p className="text-sky-400 text-[10px] uppercase tracking-wider mb-1 font-bold">Position Ouverte</p>
                                                <div className="flex items-baseline gap-2">
                                                    <span className="text-xl font-bold text-white">{openTrade.quantity} unités</span>
                                                    <span className="text-sm text-gray-400">@ ${openTrade.entry_price.toFixed(2)}</span>
                                                    {openTrade.pnl != null && (
                                                        <span className={`text-sm font-bold ${openTrade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            {openTrade.pnl >= 0 ? '+' : ''}${openTrade.pnl.toFixed(2)}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            {editingTargets ? (
                                                <div className="flex gap-2 items-center flex-wrap">
                                                    <input type="number" placeholder={`SL (${openTrade.stop_loss?.toFixed(2)})`} value={newSL} onChange={e => setNewSL(e.target.value)}
                                                        className="w-28 bg-red-500/10 border border-red-500/30 rounded-lg px-2 py-1 text-white text-xs focus:outline-none focus:ring-1 focus:ring-red-500" />
                                                    <input type="number" placeholder={`TP (${openTrade.take_profit?.toFixed(2)})`} value={newTP} onChange={e => setNewTP(e.target.value)}
                                                        className="w-28 bg-green-500/10 border border-green-500/30 rounded-lg px-2 py-1 text-white text-xs focus:outline-none focus:ring-1 focus:ring-green-500" />
                                                    <button onClick={handleUpdateTargets} disabled={actionLoading} className="px-3 py-1 bg-sky-500 text-black text-xs font-bold rounded-lg hover:bg-sky-400 disabled:opacity-50">✓ Sauver</button>
                                                    <button onClick={() => setEditingTargets(false)} className="px-3 py-1 bg-gray-700 text-gray-300 text-xs rounded-lg hover:bg-gray-600">✕</button>
                                                </div>
                                            ) : (
                                                <div className="flex gap-2 items-center flex-wrap">
                                                    <div className="bg-green-500/20 border border-green-500/40 px-3 py-1.5 rounded-lg text-center">
                                                        <p className="text-[9px] text-green-400 uppercase font-bold">Take Profit</p>
                                                        <p className="text-sm font-mono font-bold text-white">${openTrade.take_profit?.toFixed(2) || '—'}</p>
                                                    </div>
                                                    <div className="bg-red-500/20 border border-red-500/40 px-3 py-1.5 rounded-lg text-center">
                                                        <p className="text-[9px] text-red-400 uppercase font-bold">Stop Loss</p>
                                                        <p className="text-sm font-mono font-bold text-white">${openTrade.stop_loss?.toFixed(2) || '—'}</p>
                                                    </div>
                                                    <button onClick={() => { setEditingTargets(true); setNewSL(openTrade.stop_loss?.toFixed(2) || ''); setNewTP(openTrade.take_profit?.toFixed(2) || '') }}
                                                        className="text-xs text-gray-400 hover:text-sky-400 border border-gray-700 hover:border-sky-500/50 px-2 py-1.5 rounded-lg transition-colors" title="Modifier les cibles">✏️</button>
                                                </div>
                                            )}
                                        </div>

                                        <div className="flex gap-2 mt-3 flex-wrap">
                                            <button onClick={handleSell} disabled={actionLoading}
                                                className="flex-1 min-w-[100px] py-2 bg-red-500/20 border border-red-500/50 text-red-400 text-sm font-bold rounded-lg hover:bg-red-500/30 transition-colors disabled:opacity-50">
                                                🔴 Vendre au marché
                                            </button>
                                            <button onClick={() => setShowAddForm(!showAddForm)} disabled={actionLoading}
                                                className="flex-1 min-w-[100px] py-2 bg-green-500/20 border border-green-500/50 text-green-400 text-sm font-bold rounded-lg hover:bg-green-500/30 transition-colors disabled:opacity-50">
                                                ➕ Renforcer
                                            </button>
                                        </div>
                                        {showAddForm && (
                                            <div className="flex gap-2 mt-2 items-center">
                                                <input type="number" min="0" step="0.01" value={addQty} onChange={e => setAddQty(e.target.value)}
                                                    placeholder="Quantité..."
                                                    className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:ring-1 focus:ring-green-500" />
                                                <button onClick={handleAddToPosition} disabled={actionLoading}
                                                    className="px-4 py-1.5 bg-green-500 text-black text-xs font-bold rounded-lg hover:bg-green-400 disabled:opacity-50">Ajouter</button>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="md:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                                        <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-3 font-bold">Achat Manuel</p>
                                        <div className="flex flex-wrap gap-3 items-end">
                                            <div className="flex-1 min-w-[100px]">
                                                <label className="text-[9px] text-gray-500 block mb-1">Qté</label>
                                                <input type="number" value={buyQty} onChange={e => setBuyQty(e.target.value)}
                                                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs focus:ring-1 focus:ring-sky-500" />
                                            </div>
                                            <div className="flex-1 min-w-[100px]">
                                                <label className="text-[9px] text-red-500/70 block mb-1">Stop Loss ($)</label>
                                                <input type="number" value={buySL} onChange={e => setBuySL(e.target.value)} placeholder="Optionnel"
                                                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs focus:ring-1 focus:ring-red-500" />
                                            </div>
                                            <div className="flex-1 min-w-[100px]">
                                                <label className="text-[9px] text-green-500/70 block mb-1">Take Profit ($)</label>
                                                <input type="number" value={buyTP} onChange={e => setBuyTP(e.target.value)} placeholder="Optionnel"
                                                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs focus:ring-1 focus:ring-green-500" />
                                            </div>
                                            <button onClick={handleBuy} disabled={actionLoading}
                                                className="bg-sky-500 hover:bg-sky-400 text-black font-bold h-[34px] px-6 rounded-lg text-xs transition-colors disabled:opacity-50">
                                                Acheter
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Justification IA */}
                            {openTrade && (
                                <div className="bg-gray-800/50 border-l-4 border-sky-500 rounded-r-xl p-4">
                                    <p className="text-xs text-sky-400 font-bold mb-1 flex items-center gap-1">
                                        <span>🤖</span> Pourquoi l'IA a ouvert cette position :
                                    </p>
                                    <p className="text-sm text-gray-300 italic">
                                        {openTrade.justification || "Analyse technique multicritère (RSI, Volatilité, Sentiments) — Signal d'achat confirmé par l'algorithme de trading."}
                                    </p>
                                </div>
                            )}

                            {/* Graphique */}
                            <div className="bg-gray-800 rounded-xl p-4 h-[350px]">
                                <h3 className="text-[10px] font-semibold text-gray-500 mb-4 uppercase tracking-wider">Évolution 6 Mois</h3>
                                <div className="h-[280px]">
                                    <Line data={chartData} options={chartOptions} />
                                </div>
                            </div>

                            {/* Description & Historique */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {info && info.summary && (
                                    <div className="bg-gray-800/30 rounded-xl p-6 border border-gray-800">
                                        <h3 className="text-[10px] font-semibold text-gray-500 mb-3 uppercase tracking-wider">À Propos</h3>
                                        <p className="text-gray-400 text-xs leading-relaxed line-clamp-6 hover:line-clamp-none transition-all cursor-default">
                                            {info.summary}
                                        </p>
                                    </div>
                                )}

                                <div className="bg-gray-800/30 rounded-xl p-6 border border-gray-800">
                                    <h3 className="text-[10px] font-semibold text-gray-500 mb-4 uppercase tracking-wider">Historique</h3>
                                    {userTrades.length > 0 ? (
                                        <div className="max-h-[200px] overflow-y-auto space-y-2 pr-2">
                                            {userTrades.map((t) => (
                                                <div key={t.id} className={`flex justify-between items-center text-xs p-2 rounded ${t.status === 'OPEN' ? 'bg-sky-500/5 border border-sky-500/20' : 'bg-gray-900/40'}`}>
                                                    <div>
                                                        <span className="text-white font-medium">{t.quantity} unités</span>
                                                        <p className="text-[10px] text-gray-500">{new Date(t.entry_date).toLocaleDateString()}</p>
                                                    </div>
                                                    <div className="text-right">
                                                        <span className="text-sky-400 font-mono">${t.entry_price.toFixed(2)}</span>
                                                        {t.status === 'OPEN' && <span className="ml-2 px-1.5 py-0.5 bg-sky-500/20 text-sky-400 rounded-[2px] text-[8px] font-bold uppercase">Live</span>}
                                                        {t.status === 'CLOSED' && t.pnl != null && (
                                                            <span className={`ml-2 text-[10px] font-bold ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-xs text-gray-600 italic">Aucune transaction.</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
