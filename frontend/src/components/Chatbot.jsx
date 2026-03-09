import { useState, useEffect, useRef } from 'react'
import { chatAPI } from '../services/apiService'

export default function Chatbot() {
    const [isOpen, setIsOpen] = useState(false)
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Bonjour ! Je suis votre assistant de trading. Comment puis-je vous aider ?' }
    ])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [highlightedId, setHighlightedId] = useState(null)
    const messagesEndRef = useRef(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    const fetchHistory = async () => {
        try {
            const res = await chatAPI.getHistory()
            if (res.data && res.data.length > 0) {
                setMessages(res.data)
            }
        } catch (error) {
            console.error("Error fetching chat history:", error)
        }
    }

    useEffect(() => {
        fetchHistory()
        // Rafraîchir toutes les 5 minutes pour voir les nouveaux rapports
        const interval = setInterval(fetchHistory, 300000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        // Écouter les demandes d'ouverture de message (depuis ActivityLog)
        const handleOpenMessage = (e) => {
            const { messageId } = e.detail;
            setIsOpen(true);
            fetchHistory(); // S'assurer que le message est chargé
            setHighlightedId(messageId);
            
            // Retirer le highlight après 5 secondes
            setTimeout(() => setHighlightedId(null), 5000);
        };

        window.addEventListener('open-chat-message', handleOpenMessage);
        return () => window.removeEventListener('open-chat-message', handleOpenMessage);
    }, []);

    useEffect(() => {
        scrollToBottom()
    }, [messages, isOpen])

    const handleSend = async () => {
        if (!input.trim()) return

        const userMessage = { role: 'user', content: input }
        const updatedMessages = [...messages, userMessage]
        setMessages(updatedMessages)
        setInput('')
        setLoading(true)

        try {
            const res = await chatAPI.send(updatedMessages)
            const botMessage = { role: 'assistant', content: res.data.response }
            setMessages(prev => [...prev, botMessage])
        } catch (error) {
            console.error("Chatbot error:", error)
            setMessages(prev => [...prev, { role: 'assistant', content: 'Erreur: Impossible de contacter le serveur.' }])
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="fixed bottom-6 right-6 z-[100]">
            {/* Bouton pour ouvrir */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="w-14 h-14 bg-sky-500 rounded-full shadow-[0_0_20px_rgba(56,189,248,0.4)] flex items-center justify-center transition-all hover:scale-110 active:scale-95 group animate-pulse-glow border-2 border-white/20"
                >
                    <div className="w-10 h-10 rounded-full overflow-hidden bg-white/10 flex items-center justify-center">
                        <img src="/logo-axiom-symbol.png" alt="Axiom Chat" className="w-full h-full object-contain" />
                    </div>
                </button>
            )}

            {/* Fenêtre de chat */}
            {isOpen && (
                <div className="w-80 h-96 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl flex flex-col animate-fade-in overflow-hidden">
                    <div className="bg-gray-800 p-3 flex justify-between items-center border-b border-gray-700">
                        <span className="font-bold text-white text-sm">Axiom Assistant</span>
                        <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white">✕</button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-3 space-y-3">
                        {messages.map((m, i) => {
                            const isHighlighted = m.id === highlightedId;
                            return (
                                <div key={m.id || i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div 
                                        className={`max-w-[80%] rounded-lg px-3 py-2 text-xs transition-all duration-1000 whitespace-pre-wrap 
                                            ${m.role === 'user' ? 'bg-sky-600 text-white' : 'bg-gray-800 text-gray-200'}
                                            ${isHighlighted ? 'ring-2 ring-sky-400 bg-sky-900/40 scale-[1.02]' : ''}
                                        `}
                                    >
                                        {m.content}
                                    </div>
                                </div>
                            );
                        })}
                        {loading && (
                            <div className="flex justify-start">
                                <div className="bg-gray-800 text-gray-200 rounded-lg px-3 py-2 text-xs italic">En train de réfléchir...</div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <div className="p-3 border-t border-gray-800 flex gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Posez une question..."
                            className="flex-1 bg-gray-800 border-none rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-sky-500"
                        />
                        <button
                            onClick={handleSend}
                            className="bg-sky-500 text-white px-3 py-2 rounded-lg text-xs"
                        >
                            ➤
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
