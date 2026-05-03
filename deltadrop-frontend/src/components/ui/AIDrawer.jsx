/**
 * AIDrawer.jsx — Floating AI Price Intelligence chat panel
 *
 * Renders a slide-in drawer from the right side of the screen.
 * Accepts a product prop and builds context automatically.
 * Shows suggested questions, chat history, and verdict badge.
 */
import { useState, useRef, useEffect } from 'react'
import {
  askDeltaDropAI,
  buildProductContext,
  buildSearchContext,
  getSuggestedQuestions,
  parseVerdictFromAnswer,
} from '../../services/ai'

// ── Verdict colors ────────────────────────────────────────────────────────────
const VERDICT_STYLE = {
  BUY_NOW: { bg: 'bg-tertiary-container',     text: 'text-on-tertiary-container', label: '✓ BUY NOW' },
  WAIT:    { bg: 'bg-primary',                text: 'text-on-primary',             label: '⏳ WAIT'   },
  NEUTRAL: { bg: 'bg-surface-container-high', text: 'text-on-surface-variant',     label: '— NEUTRAL' },
}

// ── Message bubble ────────────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const verdict = !isUser ? parseVerdictFromAnswer(msg.content) : null
  const vs = verdict ? VERDICT_STYLE[verdict] : null

  return (
    <div className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5
        ${isUser ? 'grad-primary text-on-primary' : 'bg-inverse-surface text-inverse-on-surface'}`}>
        {isUser ? 'U' : '⚡'}
      </div>

      <div className={`flex-1 ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Verdict badge for AI messages */}
        {vs && (
          <span className={`text-[10px] font-black px-2.5 py-1 rounded-full mb-2 uppercase tracking-wider ${vs.bg} ${vs.text}`}>
            {vs.label}
          </span>
        )}

        {/* Message content */}
        <div className={`text-sm leading-relaxed rounded-xl px-4 py-3 max-w-[85%]
          ${isUser
            ? 'grad-primary text-on-primary rounded-tr-sm'
            : 'bg-surface-container-low text-on-surface rounded-tl-sm'}`}>
          {msg.content.split('\n').map((line, i) => (
            <p key={i} className={line.startsWith('**') ? 'font-bold mt-2 first:mt-0' : ''}>
              {line.replace(/\*\*/g, '')}
            </p>
          ))}
        </div>

        <div className="text-[10px] text-on-surface-variant mt-1 px-1">
          {msg.time}
        </div>
      </div>
    </div>
  )
}

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex gap-3 mb-4">
      <div className="w-7 h-7 rounded-full bg-inverse-surface flex items-center justify-center text-xs flex-shrink-0">⚡</div>
      <div className="bg-surface-container-low rounded-xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map(i => (
            <span key={i} className="w-1.5 h-1.5 rounded-full bg-on-surface-variant animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main drawer ───────────────────────────────────────────────────────────────
export default function AIDrawer({ product, searchResults, isOpen, onClose }) {
  const [messages,   setMessages]   = useState([])
  const [input,      setInput]      = useState('')
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef       = useRef(null)

  const suggested = getSuggestedQuestions(product)

  // Build context once when product changes
  const context = product
    ? buildProductContext(product)
    : searchResults?.length
      ? buildSearchContext('', searchResults)
      : ''

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Focus input when opened
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 300)
  }, [isOpen])

  // Welcome message when product changes
  useEffect(() => {
    if (product && isOpen) {
      const bestPrice = product.price || 'N/A'
      const bestRetailer = product.retailers?.[0]?.name || 'a verified retailer'
      setMessages([{
        role: 'assistant',
        content: `I've loaded live pricing data for **${product.name}**.\n\nCurrent best price: **${bestPrice}** on ${bestRetailer}.\n\nAsk me anything — should you buy now, which retailer wins, or when the price will drop.`,
        time: now(),
      }])
    }
  }, [product?.id, isOpen])

  async function send(question = input.trim()) {
    if (!question || loading) return
    setInput('')
    setError(null)

    const userMsg = { role: 'user', content: question, time: now() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const answer = await askDeltaDropAI(context, question)
      setMessages(prev => [...prev, { role: 'assistant', content: answer, time: now() }])
    } catch (e) {
      setError(e.message || 'AI service unavailable. Check your API key.')
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  function clearChat() {
    setMessages([])
    setError(null)
  }

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div className="fixed inset-0 z-[90] bg-on-surface/20"
          style={{ backdropFilter: 'blur(2px)' }}
          onClick={onClose} />
      )}

      {/* Drawer */}
      <div
        className="fixed top-0 right-0 h-full z-[100] flex flex-col"
        style={{
          width:      '400px',
          maxWidth:   '95vw',
          background: 'var(--color-surface-container-lowest, #fff)',
          boxShadow:  '-8px 0 40px rgba(24,28,30,0.14)',
          transform:  isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.32s cubic-bezier(0.22,1,0.36,1)',
        }}>

        {/* Header */}
        <div className="grad-primary px-5 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center">
              <span className="material-symbols-outlined fill-icon text-white text-base">psychology</span>
            </div>
            <div>
              <div className="font-headline font-black text-white text-sm">Delta Intelligence</div>
              <div className="text-on-primary-container text-[10px] font-medium uppercase tracking-wider">AI Price Engine · Google Gemini</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button onClick={clearChat}
                className="text-on-primary-container hover:text-white text-[10px] font-semibold uppercase tracking-wide transition-colors">
                Clear
              </button>
            )}
            <button onClick={onClose}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors">
              <span className="material-symbols-outlined text-white text-lg">close</span>
            </button>
          </div>
        </div>

        {/* Product context strip */}
        {product && (
          <div className="px-4 py-3 bg-surface-container-low flex items-center gap-3 flex-shrink-0"
            style={{ borderBottom: '1px solid rgba(195,198,214,0.15)' }}>
            <div className="w-9 h-9 rounded-lg bg-surface-container flex items-center justify-center text-xl flex-shrink-0">
              {product.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-on-surface truncate">{product.name}</div>
              <div className="text-[10px] text-on-surface-variant">
                Best: <strong className="text-tertiary-container">{product.price || 'N/A'}</strong> · {product.category || 'Product'}
              </div>
            </div>
            {product.aiVerdict && (
              <span className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase flex-shrink-0
                ${product.aiVerdict === 'BUY NOW'
                  ? 'bg-tertiary-container/20 text-tertiary-container'
                  : 'bg-primary/10 text-primary'}`}>
                {product.aiVerdict}
              </span>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 && !loading ? (
            /* Empty state with suggested questions */
            <div>
              <div className="text-center py-6">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <span className="material-symbols-outlined text-primary text-3xl">auto_awesome</span>
                </div>
                <div className="font-headline font-bold text-sm text-on-surface mb-1">Price Intelligence Ready</div>
                <p className="text-xs text-on-surface-variant leading-relaxed max-w-xs mx-auto">
                  Ask anything about pricing, timing, or which retailer to buy from.
                </p>
              </div>

              {/* Suggested questions */}
              {suggested.length > 0 && (
                <div>
                  <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-3 px-1">
                    Suggested
                  </div>
                  <div className="space-y-2">
                    {suggested.slice(0, 4).map((q, i) => (
                      <button key={i} onClick={() => send(q)}
                        className="w-full text-left px-4 py-3 rounded-xl bg-surface-container-low hover:bg-secondary-container/40 hover:text-primary transition-colors text-sm text-on-surface-variant font-medium leading-snug">
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Message list */
            <>
              {messages.map((msg, i) => (
                <MessageBubble key={i} msg={msg} />
              ))}
              {loading && <TypingIndicator />}
              {error && (
                <div className="mx-1 mb-4 px-4 py-3 rounded-xl bg-red-50 text-red-700 text-xs leading-relaxed">
                  <strong>Error:</strong> {error}
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Quick questions (shown after first message) */}
        {messages.length > 0 && suggested.length > 0 && (
          <div className="px-4 pb-2 flex gap-2 overflow-x-auto flex-shrink-0"
            style={{ scrollbarWidth: 'none' }}>
            {suggested.slice(0, 3).map((q, i) => (
              <button key={i} onClick={() => send(q)} disabled={loading}
                className="flex-shrink-0 px-3 py-1.5 rounded-full bg-surface-container text-on-surface-variant text-[11px] font-medium hover:bg-secondary-container hover:text-primary transition-colors disabled:opacity-50 whitespace-nowrap">
                {q.length > 35 ? q.slice(0, 35) + '…' : q}
              </button>
            ))}
          </div>
        )}

        {/* Input area */}
        <div className="px-4 pb-5 pt-3 flex-shrink-0" style={{ borderTop: '1px solid rgba(195,198,214,0.15)' }}>
          <div className="flex items-end gap-2">
            <div className="flex-1 bg-surface-container-highest rounded-xl overflow-hidden flex items-end">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about price timing, deals, or retailers…"
                rows={1}
                disabled={loading}
                style={{ resize: 'none', minHeight: '40px', maxHeight: '120px' }}
                className="w-full px-4 py-3 text-sm text-on-surface bg-transparent border-none outline-none placeholder:text-on-surface-variant disabled:opacity-60 font-body"
                onInput={e => {
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
                }}
              />
            </div>
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="w-10 h-10 rounded-xl grad-primary text-on-primary flex items-center justify-center hover:opacity-90 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0">
              <span className="material-symbols-outlined fill-icon text-lg">
                {loading ? 'hourglass_empty' : 'send'}
              </span>
            </button>
          </div>
          <div className="text-[10px] text-on-surface-variant text-center mt-2">
            ↵ send · Shift+↵ newline · Powered by Google Gemini
          </div>
        </div>
      </div>
    </>
  )
}

function now() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}
