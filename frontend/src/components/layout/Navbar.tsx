import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Home, 
  Zap, 
  Bot, 
  Target, 
  BarChart3,
  TrendingUp,
  Menu,
  X,
  Beaker,
  ArrowUpDown,
  Wand2,
  Hammer,
  Shield
} from 'lucide-react';
import { Button } from '../ui/Button';

interface NavbarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ sidebarOpen, setSidebarOpen }) => {
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'High Alchemy', href: '/high-alchemy', icon: Zap },
    { name: 'Decanting', href: '/decanting', icon: Beaker },
    { name: 'Flipping', href: '/flipping', icon: ArrowUpDown },
    { name: 'Magic & Runes', href: '/magic-runes', icon: Wand2 },
    { name: 'Crafting', href: '/crafting', icon: Hammer },
    { name: 'Set Combining', href: '/set-combining', icon: Shield },
  ];

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="glass border-b border-white/10 sticky top-0 z-50"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Mobile Menu Toggle */}
          <div className="flex items-center">
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
            
            <Link to="/" className="flex items-center ml-4 md:ml-0">
              <div className="w-8 h-8 bg-gradient-to-br from-accent-400 to-accent-600 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:block flex-1 max-w-4xl">
            <div className="flex items-center justify-center space-x-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center space-x-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                      isActive
                        ? 'bg-accent-500/20 text-accent-400 border border-accent-500/30'
                        : 'text-gray-300 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span className="whitespace-nowrap text-xs">{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-2">
            {/* AI Trading Assistant Button */}
            <Link
              to="/recommendations"
              className={`flex items-center space-x-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                location.pathname === '/recommendations'
                  ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-blue-300 border border-blue-400/30'
                  : 'bg-gradient-to-r from-blue-500/10 to-purple-500/10 text-blue-200 border border-blue-500/20 hover:from-blue-500/20 hover:to-purple-500/20 hover:text-white'
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">AI</span>
            </Link>
            
            {/* Analytics Button */}
            <Link
              to="/analytics"
              className={`flex items-center space-x-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                location.pathname === '/analytics'
                  ? 'bg-accent-500/20 text-accent-400 border border-accent-500/30'
                  : 'text-gray-300 hover:bg-white/10 hover:text-white'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">Analytics</span>
            </Link>
            
            {/* Goal Planning Button */}
            <Link
              to="/planning"
              className={`flex items-center space-x-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                location.pathname === '/planning'
                  ? 'bg-accent-500/20 text-accent-400 border border-accent-500/30'
                  : 'text-gray-300 hover:bg-white/10 hover:text-white'
              }`}
            >
              <Target className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">Planning</span>
            </Link>
          </div>
        </div>
      </div>
    </motion.nav>
  );
};