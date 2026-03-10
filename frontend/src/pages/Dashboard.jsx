/**
 * Dashboard.jsx — Interface principale de Trading Bach Bot.
 * Accessible uniquement aux utilisateurs connectés (protégé par ProtectedRoute).
 */
import { useState } from 'react'
import Header from '../layout/Header'
import NewsPanel from '../components/NewsPanel'
import SignalPanel from '../components/SignalPanel'
import PortfolioChart from '../components/PortfolioChart'
import PositionsTable from '../components/PositionsTable'
import Chatbot from '../components/Chatbot'
import StockDetailsModal from '../components/StockDetailsModal'
import ManualTradeModal from '../components/ManualTradeModal'
import AccountPanel from '../components/AccountPanel'
import ActivityLog from '../components/ActivityLog'
import TransactionHistory from '../components/TransactionHistory'
import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
    const { profile } = useAuth()
    const [selectedStock, setSelectedStock] = useState(null)
    const [manualTradeSymbol, setManualTradeSymbol] = useState(null)
    const [showAccountPanel, setShowAccountPanel] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)

    const handleRefresh = () => {
        setRefreshKey(k => k + 1)
        window.dispatchEvent(new CustomEvent('refresh-signals'))
    }

    return (
        <div className="min-h-screen flex flex-col gap-6 pb-12">
            <Header
                onSearch={setSelectedStock}
                onOpenAccount={() => setShowAccountPanel(true)}
                userProfile={profile}
                key={refreshKey}
            />

            <main className="max-w-[1600px] w-full mx-auto px-6 grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1">
                {/* 5. Actualités (Dernier sur mobile) */}
                <div className="lg:col-span-1 h-auto lg:h-[calc(100vh-140px)] order-5 lg:order-1 flex flex-col gap-6">
                    <NewsPanel />
                </div>
                
                {/* 1 & 2. Graphique et Positions */}
                <div className="lg:col-span-2 flex flex-col gap-6 order-1 lg:order-2">
                    <div className="h-[300px] lg:h-[400px] order-1">
                        <PortfolioChart />
                    </div>
                    <div className="flex-1 order-2">
                        <PositionsTable onSelectStock={setSelectedStock} key={refreshKey} />
                    </div>
                </div>

                {/* 3 & 4. Activité IA, Conseils et Historique */}
                <div className="lg:col-span-1 flex flex-col gap-6 h-auto lg:h-[calc(100vh-140px)] order-2 lg:order-3">
                    <div className="h-[200px] order-1">
                        <ActivityLog />
                    </div>
                    <div className="h-[250px] order-3">
                        <TransactionHistory />
                    </div>
                    <div className="flex-1 overflow-hidden order-2">
                        <SignalPanel onSelectStock={setSelectedStock} />
                    </div>
                </div>
            </main>

            <Chatbot />

            {selectedStock && (
                <StockDetailsModal symbol={selectedStock} onClose={() => setSelectedStock(null)} />
            )}
            {manualTradeSymbol && (
                <ManualTradeModal
                    symbol={manualTradeSymbol}
                    onClose={() => setManualTradeSymbol(null)}
                    onSuccess={handleRefresh}
                />
            )}
            {showAccountPanel && (
                <AccountPanel onClose={() => setShowAccountPanel(false)} onRefresh={handleRefresh} />
            )}
        </div>
    )
}
