import { useState, useCallback, useEffect } from 'react'
import { auth, setAuthChangeCallback } from '../services/api'
import AuthContext from './auth-context'

export function AuthProvider({ children }) {
  const [user, setUser] = useState (() => {
    try { return JSON.parse(localStorage.getItem('dd_user')) } catch { return null }
  })
  const [token, setToken] = useState(() => localStorage.getItem('dd_token'))
  const [isInitializing, setIsInitializing] = useState(true)

  // Sync state when api.js updates tokens (via refresh or logout)
  useEffect(() => {
    setAuthChangeCallback(({ token, user }) => {
      setToken(token)
      setUser(user)
    })
    return () => setAuthChangeCallback(null)
  }, [])

  const login = useCallback((userData, accessToken, refreshToken) => {
    localStorage.setItem('dd_token',   accessToken)
    localStorage.setItem('dd_refresh', refreshToken)
    localStorage.setItem('dd_user',    JSON.stringify(userData))
    setUser(userData)
    setToken(accessToken)
  }, [])

  const logout = useCallback(async () => {
    try {
      await auth.logout()
    } catch (_) {}
    localStorage.removeItem('dd_token')

    localStorage.removeItem('dd_refresh')
    localStorage.removeItem('dd_user')
    setUser(null)
    setToken(null)
  }, [])

  // Auto-rehydration on mount
  useEffect(() => {
    let isMounted = true;
    
    // Safety timeout: Never stay in loading state for more than 8 seconds
    const safetyTimeout = setTimeout(() => {
      if (isMounted) {
        console.warn("[Auth] Initialization safety timeout reached");
        setIsInitializing(false);
      }
    }, 8000);

    const rehydrate = async () => {
      try {
        // Dynamic import to avoid circular dependency and ensure services/api is ready
        const { validateTokenPair, clearTokens } = await import('../services/api')
        
        const token = localStorage.getItem('dd_token')
        const refresh = localStorage.getItem('dd_refresh')
        
        if (!token && !refresh) {
          if (isMounted) setIsInitializing(false)
          return
        }
        
        // Validate token pair before attempting any API call
        if (!validateTokenPair()) {
          if (isMounted) setIsInitializing(false)
          return
        }
        
        try {
          const me = await auth.me()
          if (isMounted) {
            setUser(me)
            localStorage.setItem('dd_user', JSON.stringify(me))
          }
        } catch (err) {
          console.warn("[Auth] Me API failed:", err.message)
          if (isMounted) {
            clearTokens()
            setUser(null)
            setToken(null)
          }
        }
      } catch (err) {
        console.error("[Auth] Global rehydration failure:", err)
      } finally {
        if (isMounted) setIsInitializing(false)
        clearTimeout(safetyTimeout)
      }
    }

    rehydrate()

    return () => {
      isMounted = false
      clearTimeout(safetyTimeout)
    }
  }, []) // Empty array to ensure it only runs once on mount

  const updateUser = useCallback((userData) => {
    localStorage.setItem('dd_user', JSON.stringify(userData))
    setUser(userData)
  }, [])

  return (
    <AuthContext.Provider value={{ 
      user, 
      token, 
      isLoggedIn: !!user && !!token, 
      isInitializing,
      login, 
      logout, 
      updateUser 
    }}>
      {children}
    </AuthContext.Provider>
  )
}
