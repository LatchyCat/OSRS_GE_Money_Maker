/**
 * Context provider for reactive trading WebSocket connection.
 * 
 * This provider ensures only ONE WebSocket connection is created and shared
 * across all components that need real-time trading data, preventing the
 * infinite loop issue caused by multiple concurrent connections.
 */

import React, { createContext, useContext, ReactNode } from 'react'
import { useReactiveTradingSocket, type UseReactiveTradingSocketReturn } from '../hooks/useReactiveTradingSocket'

// Create the context
const ReactiveTradingContext = createContext<UseReactiveTradingSocketReturn | undefined>(undefined)

// Provider component
interface ReactiveTradingProviderProps {
  children: ReactNode
}

export const ReactiveTradingProvider: React.FC<ReactiveTradingProviderProps> = ({ children }) => {
  // Create ONE WebSocket connection that will be shared by all components
  const tradingSocket = useReactiveTradingSocket()

  return (
    <ReactiveTradingContext.Provider value={tradingSocket}>
      {children}
    </ReactiveTradingContext.Provider>
  )
}

// Hook to consume the context
export const useReactiveTradingContext = (): UseReactiveTradingSocketReturn => {
  const context = useContext(ReactiveTradingContext)
  
  if (context === undefined) {
    throw new Error('useReactiveTradingContext must be used within a ReactiveTradingProvider')
  }
  
  return context
}