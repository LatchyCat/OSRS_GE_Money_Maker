import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Cpu, 
  Database, 
  Wifi, 
  Zap, 
  Activity, 
  Clock, 
  TrendingUp,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

interface SystemMetric {
  id: string;
  label: string;
  value: number;
  unit: string;
  status: 'optimal' | 'warning' | 'critical';
  icon: React.ComponentType<any>;
}

interface HolographicHUDProps {
  className?: string;
  showPerformanceMetrics?: boolean;
}

export const HolographicHUD: React.FC<HolographicHUDProps> = ({
  className = '',
  showPerformanceMetrics = true
}) => {
  const [metrics, setMetrics] = useState<SystemMetric[]>([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'reconnecting' | 'disconnected'>('connected');

  // Initialize system metrics
  useEffect(() => {
    const initialMetrics: SystemMetric[] = [
      {
        id: 'api_latency',
        label: 'API Latency',
        value: 45 + Math.random() * 20,
        unit: 'ms',
        status: 'optimal',
        icon: Zap
      },
      {
        id: 'data_freshness',
        label: 'Data Freshness',
        value: 95 + Math.random() * 5,
        unit: '%',
        status: 'optimal',
        icon: Database
      },
      {
        id: 'market_sync',
        label: 'Market Sync',
        value: 99.2 + Math.random() * 0.8,
        unit: '%',
        status: 'optimal',
        icon: TrendingUp
      },
      {
        id: 'system_load',
        label: 'System Load',
        value: 25 + Math.random() * 30,
        unit: '%',
        status: 'optimal',
        icon: Cpu
      }
    ];
    
    setMetrics(initialMetrics);
  }, []);

  // Update metrics periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prevMetrics => 
        prevMetrics.map(metric => {
          let newValue = metric.value;
          let newStatus = metric.status;
          
          // Simulate realistic fluctuations
          switch (metric.id) {
            case 'api_latency':
              newValue = Math.max(20, Math.min(200, newValue + (Math.random() - 0.5) * 10));
              newStatus = newValue > 100 ? 'warning' : newValue > 150 ? 'critical' : 'optimal';
              break;
            case 'data_freshness':
              newValue = Math.max(80, Math.min(100, newValue + (Math.random() - 0.5) * 2));
              newStatus = newValue < 90 ? 'warning' : newValue < 85 ? 'critical' : 'optimal';
              break;
            case 'market_sync':
              newValue = Math.max(95, Math.min(100, newValue + (Math.random() - 0.5) * 1));
              newStatus = newValue < 98 ? 'warning' : newValue < 96 ? 'critical' : 'optimal';
              break;
            case 'system_load':
              newValue = Math.max(10, Math.min(90, newValue + (Math.random() - 0.5) * 8));
              newStatus = newValue > 70 ? 'warning' : newValue > 85 ? 'critical' : 'optimal';
              break;
          }
          
          return { ...metric, value: newValue, status: newStatus };
        })
      );
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);

  // Update time
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);

  // Simulate connection status changes
  useEffect(() => {
    const interval = setInterval(() => {
      const rand = Math.random();
      if (rand < 0.95) {
        setConnectionStatus('connected');
      } else if (rand < 0.98) {
        setConnectionStatus('reconnecting');
      } else {
        setConnectionStatus('disconnected');
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'optimal':
        return 'text-green-400 shadow-green-400/50';
      case 'warning':
        return 'text-yellow-400 shadow-yellow-400/50';
      case 'critical':
        return 'text-red-400 shadow-red-400/50';
      default:
        return 'text-gray-400 shadow-gray-400/50';
    }
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <CheckCircle className="w-3 h-3 text-green-400" />;
      case 'reconnecting':
        return <Activity className="w-3 h-3 text-yellow-400 animate-pulse" />;
      case 'disconnected':
        return <AlertTriangle className="w-3 h-3 text-red-400" />;
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className={`fixed top-20 right-4 sm:top-24 sm:right-6 lg:top-20 lg:right-6 z-40 w-64 sm:w-72 lg:w-80 ${className}`}>
      {/* Main HUD Container */}
      <motion.div
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        className="bg-black/60 backdrop-blur-xl border border-cyan-400/30 rounded-lg overflow-hidden shadow-2xl shadow-cyan-400/20"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-2 bg-cyan-400/10 border-b border-cyan-400/20">
          <div className="flex items-center space-x-2">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            >
              <Activity className="w-3 h-3 text-cyan-400" />
            </motion.div>
            <span className="text-xs font-medium text-cyan-300">SYSTEM HUD</span>
          </div>
          
          <div className="flex items-center space-x-2">
            {getConnectionIcon()}
            <span className="text-xs text-gray-300 font-mono">
              {formatTime(currentTime)}
            </span>
          </div>
        </div>

        {/* Performance Metrics */}
        {showPerformanceMetrics && (
          <div className="p-2 space-y-2">
            {metrics.map((metric) => {
              const Icon = metric.icon;
              return (
                <div key={metric.id} className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <Icon className={`w-3 h-3 ${getStatusColor(metric.status)}`} />
                    <span className="text-gray-300 w-16 truncate">{metric.label}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {/* Metric Bar */}
                    <div className="w-12 h-1 bg-black/50 rounded-full overflow-hidden">
                      <motion.div
                        className={`h-full ${
                          metric.status === 'optimal' ? 'bg-green-400' :
                          metric.status === 'warning' ? 'bg-yellow-400' :
                          'bg-red-400'
                        }`}
                        initial={{ width: 0 }}
                        animate={{ 
                          width: `${metric.id === 'system_load' ? metric.value : 
                                  metric.id === 'api_latency' ? Math.min(metric.value / 2, 100) :
                                  metric.value}%` 
                        }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    
                    {/* Value */}
                    <span className={`font-mono ${getStatusColor(metric.status)} text-right w-12`}>
                      {metric.value.toFixed(metric.id === 'api_latency' ? 0 : 1)}{metric.unit}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* System Status */}
        <div className="p-2 border-t border-cyan-400/20 bg-black/40">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-1">
              <Wifi className="w-3 h-3 text-cyan-400" />
              <span className="text-cyan-300 capitalize">{connectionStatus}</span>
            </div>
            
            <div className="flex items-center space-x-1">
              <Clock className="w-3 h-3 text-gray-400" />
              <span className="text-gray-300">
                {Math.floor(Date.now() / 1000) % 3600}s
              </span>
            </div>
          </div>
        </div>

        {/* Scanning Animation */}
        <div className="absolute inset-0 pointer-events-none">
          <motion.div
            className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent"
            animate={{
              top: ['0%', '100%', '0%']
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            style={{
              filter: 'blur(0.5px)',
              boxShadow: '0 0 8px rgba(6, 182, 212, 0.6)'
            }}
          />
        </div>

        {/* Corner Indicators */}
        <div className="absolute top-1 right-1 w-1 h-1 bg-cyan-400 rounded-full animate-pulse shadow-lg shadow-cyan-400/75" />
        <div className="absolute bottom-1 left-1 w-1 h-1 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/75" />
      </motion.div>
    </div>
  );
};