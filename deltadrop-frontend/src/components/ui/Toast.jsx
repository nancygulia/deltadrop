import { useState, useCallback, useEffect } from 'react'

let _addToast = null

export function toast(msg, type = 'info') {
  if (_addToast) _addToast(msg, type)
}

export default function ToastProvider() {
  const [toasts, setToasts] = useState([])

  const add = useCallback((msg, type) => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, msg, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  useEffect(() => { _addToast = add; return () => { _addToast = null } }, [add])

  const colors = { success: 'bg-tertiary-container text-on-tertiary-container', error: 'bg-red-700 text-white', info: 'bg-primary text-on-primary', neutral: 'bg-inverse-surface text-inverse-on-surface' }
  const icons  = { success: 'check_circle', error: 'error', info: 'info', neutral: 'minimize' }

  return (
    <div className="fixed bottom-6 right-6 z-[999] flex flex-col gap-3 pointer-events-none">
      {toasts.map(t => (
        <div key={t.id} className={`${colors[t.type]||colors.info} flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium shadow-float min-w-[220px] animate-fade-up pointer-events-auto`}>
          <span className="material-symbols-outlined fill-icon text-base">{icons[t.type]||'info'}</span>
          {t.msg}
        </div>
      ))}
    </div>
  )
}
