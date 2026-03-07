/**
 * Header.jsx — Bandeau principal du Trading Bach Bot.
 * Affiche : nom de l'app, solde actuel, bouton cycle manuel, statut.
 */
import { useState, useEffect } from 'react'
import { portfolioAPI, signalsAPI, marketAPI } from '../services/apiService'
import { useAuth } from '../context/AuthContext'

export default function Header({ onSearch, onOpenAccount, userProfile }) {
    const { user, signOut } = useAuth()
    const [capital, setCapital] = useState(null)
    const [totalValue, setTotalValue] = useState(null)
    const [running, setRunning] = useState(false)
    const [lastCycle, setLastCycle] = useState(null)
    const [searchInput, setSearchInput] = useState('')

    useEffect(() => {
        fetchPortfolio()
        const interval = setInterval(fetchPortfolio, 30000)
        return () => clearInterval(interval)
    }, [])

    async function fetchPortfolio() {
        try {
            const res = await portfolioAPI.getSummary()
            setCapital(res.data.capital)
            setTotalValue(res.data.valeur_totale)
        } catch (e) { /* silencieux */ }
    }

    async function handleRunCycle() {
        setRunning(true)
        try {
            await signalsAPI.runCycle()
            setLastCycle(new Date().toLocaleTimeString('fr-FR'))
            await fetchPortfolio()
            // Déclencher un rafraîchissement global des signaux
            window.dispatchEvent(new CustomEvent('refresh-signals'))
        } catch (e) {
            console.error("Erreur cycle:", e)
            alert("Erreur lors du cycle: " + (e.response?.data?.detail || e.message))
        }
        finally { setRunning(false) }
    }

    const pnl = totalValue != null && capital != null ? totalValue - 10000 : null
    const pnlColor = pnl == null ? '' : pnl >= 0 ? 'text-green-400' : 'text-red-400'

    return (
        <header className="sticky top-0 z-50 border-b border-gray-800 bg-dark-900/95 backdrop-blur-md">
            <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
                {/* Logo & Titre (Masqué sur mobile pour laisser place au P&L) */}
                <div className="hidden lg:flex items-center gap-3">
                    <img src="/logo-axiom.png" alt="Axiom Logo" className="h-10 w-auto object-contain" />
                    <div className="hidden sm:block">
                        <span className="text-[11px] text-gray-500 block">V1 — Simulation</span>
                    </div>
                </div>

                {/* Stat P&L pour Mobile (Haut Gauche) */}
                <div className="lg:hidden flex flex-col">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">P&L</p>
                    <p className={`font-mono font-bold text-sm ${pnlColor}`}>
                        {pnl != null ? `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(0)}` : '—'}
                    </p>
                </div>

                {/* Stats centrales (Uniquement sur Desktop) */}
                <div className="hidden lg:flex items-center gap-6">
                    <div className="text-center group relative">
                        <p className="text-[11px] text-gray-500 uppercase tracking-wide">Solde liquide</p>
                        <p className="font-mono font-bold text-sky-400 text-lg">
                            {capital != null ? `$${capital.toFixed(2)}` : '—'}
                        </p>
                        <button
                            onClick={() => {
                                fetchPortfolio();
                                window.dispatchEvent(new CustomEvent('refresh-signals'));
                            }}
                            className="absolute -right-5 top-1/2 -translate-y-1/2 text-gray-600 hover:text-sky-400 transition-colors text-xs p-1"
                            title="Actualiser tout"
                        >
                            ↻
                        </button>
                    </div>
                    <div className="w-px h-8 bg-gray-700" />
                    <div className="text-center">
                        <p className="text-[11px] text-gray-500 uppercase tracking-wide">Valeur totale</p>
                        <p className="font-mono font-bold text-white text-lg">
                            {totalValue != null ? `$${totalValue.toFixed(2)}` : '—'}
                        </p>
                    </div>
                    <div className="w-px h-8 bg-gray-700" />
                    <div className="text-center font-bold">
                        <p className="text-[11px] text-gray-500 uppercase tracking-wide">P&L</p>
                        <p className={`font-mono font-bold text-lg ${pnlColor}`}>
                            {pnl != null ? `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}` : '—'}
                        </p>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 lg:gap-3">
                    <form
                        onSubmit={async (e) => {
                            e.preventDefault();
                            if (!searchInput.trim()) return;

                            let ticker = searchInput.trim().toUpperCase();

                            // Si c'est un nom d'entreprise (plus de 4 chars ou contient espace), demander à l'IA
                            if (ticker.length > 4 || ticker.includes(' ')) {
                                try {
                                    const res = await marketAPI.searchTicker(searchInput.trim());
                                    ticker = res.data.suggested_ticker;
                                } catch (err) {
                                    console.error("AI Search Error:", err);
                                }
                            }

                            if (onSearch) {
                                onSearch(ticker);
                                setSearchInput('');
                            }
                        }}
                        className="relative hidden lg:block"
                    >
                        <input
                            type="text"
                            placeholder="Chercher (ex: Apple ou AAPL)"
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            className="bg-gray-800 border border-gray-700 rounded-lg pl-3 pr-8 py-1.5 text-xs text-white focus:ring-1 focus:outline-none focus:ring-sky-500 w-48 transition-all"
                        />
                        <button type="submit" className="absolute right-2 top-1.5 opacity-50 hover:opacity-100">🔍</button>
                    </form>

                    {lastCycle && (
                        <span className="text-[11px] text-gray-500 hidden lg:block">Dernier cycle : {lastCycle}</span>
                    )}
                    
                    <button
                        onClick={handleRunCycle}
                        disabled={running}
                        className={`bg-sky-500 hover:bg-sky-400 text-white font-bold py-1.5 px-3 rounded-lg flex items-center gap-2 transition-all active:scale-95 disabled:opacity-50 text-xs lg:text-sm`}
                    >
                        {running ? (
                            <><div className="spinner w-3 h-3 lg:w-4 lg:h-4" /> <span className="hidden sm:inline">Analyse...</span></>
                        ) : (
                            <><span className="text-[10px] lg:text-xs">▶</span> <span className="whitespace-nowrap">Lancer cycle</span></>
                        )}
                    </button>

                    <button
                        onClick={onOpenAccount}
                        className="hidden lg:flex items-center gap-1.5 px-3 py-2 bg-gray-800 border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-white rounded-lg text-sm transition-colors"
                        title="Gestion du compte"
                    >
                        ⚙️ Compte
                    </button>

                    {/* Déconnexion Mobile/Desktop */}
                    {user && (
                        <div className="flex items-center gap-2 lg:border-l lg:border-gray-700 lg:pl-3">
                            <div className="text-right hidden lg:block">
                                <p className="text-xs text-white font-medium leading-none">{userProfile?.username || user.email?.split('@')[0]}</p>
                                <p className="text-[10px] text-gray-500 mt-0.5">{user.email}</p>
                            </div>
                            <button
                                onClick={signOut}
                                className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 flex items-center justify-center text-red-400 hover:text-red-300 transition-colors"
                                title="Se déconnecter"
                            >
                                ⏻
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    )
}
