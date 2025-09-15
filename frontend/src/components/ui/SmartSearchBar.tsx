import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Loader2, TrendingUp, TrendingDown, Zap, Package } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { itemsApi } from '../../api/itemsApi';
import type { Item } from '../../types';

interface SmartSearchBarProps {
  className?: string;
  placeholder?: string;
  onItemSelect?: (item: Item) => void;
}

interface SearchSuggestion extends Item {
  category: string;
  categoryIcon: React.ReactNode;
}

export const SmartSearchBar: React.FC<SmartSearchBarProps> = ({
  className = '',
  placeholder = 'Search items...',
  onItemSelect
}) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  
  const navigate = useNavigate();
  const searchRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('osrs-recent-searches');
    if (saved) {
      setRecentSearches(JSON.parse(saved));
    }
  }, []);

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string) => {
      if (searchQuery.length < 2) {
        setSuggestions([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await itemsApi.getItems({
          search: searchQuery,
          page_size: 8,
          ordering: '-current_profit'
        });

        // Add category information to items
        const categorizedItems: SearchSuggestion[] = response.results.map(item => ({
          ...item,
          category: categorizeItem(item.name),
          categoryIcon: getCategoryIcon(item.name)
        }));

        setSuggestions(categorizedItems);
        setIsOpen(true);
        setSelectedIndex(-1);
      } catch (error) {
        console.error('Search failed:', error);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 300),
    []
  );

  // Handle input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    
    if (value.trim()) {
      setLoading(true);
      debouncedSearch(value.trim());
    } else {
      setSuggestions([]);
      setIsOpen(false);
      setLoading(false);
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === 'Enter' && query.trim()) {
        handleSearch(query);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleItemSelect(suggestions[selectedIndex]);
        } else if (query.trim()) {
          handleSearch(query);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSelectedIndex(-1);
        searchRef.current?.blur();
        break;
    }
  };

  // Handle item selection
  const handleItemSelect = (item: SearchSuggestion) => {
    addToRecentSearches(item.name);
    setQuery('');
    setIsOpen(false);
    setSuggestions([]);
    setSelectedIndex(-1);

    if (onItemSelect) {
      onItemSelect(item);
    } else {
      // Navigate to items page with search filter
      navigate(`/items?search=${encodeURIComponent(item.name)}`);
    }
  };

  // Handle general search
  const handleSearch = (searchQuery: string) => {
    addToRecentSearches(searchQuery);
    setQuery('');
    setIsOpen(false);
    setSuggestions([]);
    navigate(`/items?search=${encodeURIComponent(searchQuery)}`);
  };

  // Add to recent searches
  const addToRecentSearches = (search: string) => {
    const updated = [search, ...recentSearches.filter(s => s !== search)].slice(0, 5);
    setRecentSearches(updated);
    localStorage.setItem('osrs-recent-searches', JSON.stringify(updated));
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Enhanced Search Input */}
      <div className="relative group">
        <div className="absolute left-3 top-1/2 transform -translate-y-1/2 z-10">
          {loading ? (
            <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
          ) : (
            <Search className="w-4 h-4 text-gray-400 group-focus-within:text-cyan-400 transition-colors" />
          )}
        </div>
        
        <input
          ref={searchRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
          placeholder={placeholder}
          className={`
            input-glass w-full pl-10 pr-4 py-2.5 text-white placeholder-gray-300
            focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-400/50
            transition-all duration-300
            group-focus-within:shadow-lg group-focus-within:shadow-cyan-500/20
            group-focus-within:bg-white/15
          `}
        />
        
        {/* Holographic border glow effect */}
        <div className="absolute inset-0 rounded-lg pointer-events-none opacity-0 group-focus-within:opacity-100 transition-opacity duration-300">
          <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-cyan-500/20 to-blue-500/20 blur-sm" />
        </div>
      </div>

      {/* Suggestions Dropdown */}
      <AnimatePresence>
        {isOpen && (suggestions.length > 0 || recentSearches.length > 0) && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="absolute top-full left-0 right-0 mt-2 z-50"
          >
            <div className="glass-card max-h-96 overflow-y-auto border border-cyan-400/30 shadow-2xl shadow-cyan-500/10">
              {/* Search Suggestions */}
              {suggestions.length > 0 && (
                <div className="space-y-1">
                  <div className="px-3 py-2 text-xs font-semibold text-cyan-300 border-b border-white/10">
                    Search Results
                  </div>
                  {suggestions.map((item, index) => (
                    <motion.div
                      key={item.item_id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={`
                        px-3 py-3 cursor-pointer transition-all duration-200
                        ${selectedIndex === index 
                          ? 'bg-cyan-500/20 border-l-2 border-cyan-400' 
                          : 'hover:bg-white/10'
                        }
                      `}
                      onClick={() => handleItemSelect(item)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 min-w-0 flex-1">
                          {/* Category Icon */}
                          <div className={`
                            p-1.5 rounded-lg flex-shrink-0
                            ${getProfitColor(item.current_profit || 0).bg}
                          `}>
                            <div className={getProfitColor(item.current_profit || 0).icon}>
                              {item.categoryIcon}
                            </div>
                          </div>
                          
                          {/* Item Info */}
                          <div className="min-w-0 flex-1">
                            <div className="text-white font-medium truncate text-sm">
                              {item.name}
                            </div>
                            <div className="text-gray-400 text-xs">
                              {item.category} • {item.members ? 'Members' : 'F2P'}
                            </div>
                          </div>
                        </div>
                        
                        {/* Profit Display */}
                        <div className="text-right flex-shrink-0 ml-3">
                          <div className={`font-bold text-sm ${getProfitColor(item.current_profit || 0).text}`}>
                            {(item.current_profit || 0) >= 0 ? '+' : ''}{(item.current_profit || 0).toLocaleString()} GP
                          </div>
                          {item.current_profit_margin && (
                            <div className="text-xs text-gray-400">
                              {item.current_profit_margin.toFixed(1)}% margin
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
              
              {/* Recent Searches */}
              {suggestions.length === 0 && recentSearches.length > 0 && (
                <div className="space-y-1">
                  <div className="px-3 py-2 text-xs font-semibold text-gray-400 border-b border-white/10">
                    Recent Searches
                  </div>
                  {recentSearches.map((search, index) => (
                    <div
                      key={search}
                      className="px-3 py-2 cursor-pointer hover:bg-white/10 transition-colors"
                      onClick={() => {
                        setQuery(search);
                        handleSearch(search);
                      }}
                    >
                      <div className="flex items-center space-x-2">
                        <Search className="w-3 h-3 text-gray-500" />
                        <span className="text-gray-300 text-sm">{search}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Helper functions
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

function categorizeItem(itemName: string): string {
  const name = itemName.toLowerCase();
  
  if (name.includes('sword') || name.includes('scimitar') || name.includes('dagger') || 
      name.includes('axe') || name.includes('mace') || name.includes('spear') ||
      name.includes('battlestaff') || name.includes('staff') || name.includes('bow')) {
    return 'Weapons';
  }
  
  if (name.includes('platebody') || name.includes('chestplate') || name.includes('helm') ||
      name.includes('shield') || name.includes('armour') || name.includes('armor') ||
      name.includes('boots') || name.includes('gloves')) {
    return 'Armor';
  }
  
  if (name.includes('potion') || name.includes('food') || name.includes('brew') ||
      name.includes('cake') || name.includes('pie')) {
    return 'Consumables';
  }
  
  if (name.includes('rune') && !name.includes(' rune ')) {
    return 'Runes';
  }
  
  if (name.includes('ore') || name.includes('bar') || name.includes('log') ||
      name.includes('raw ') || name.includes('gem')) {
    return 'Resources';
  }
  
  return 'Miscellaneous';
}

function getCategoryIcon(itemName: string): React.ReactNode {
  const category = categorizeItem(itemName);
  
  switch (category) {
    case 'Weapons':
      return <Zap className="w-3 h-3" />;
    case 'Armor':
      return <Package className="w-3 h-3" />;
    case 'Consumables':
      return <TrendingUp className="w-3 h-3" />;
    case 'Runes':
      return <Zap className="w-3 h-3" />;
    case 'Resources':
      return <Package className="w-3 h-3" />;
    default:
      return <Package className="w-3 h-3" />;
  }
}

function getProfitColor(profit: number) {
  if (profit >= 500) {
    return {
      text: 'text-green-400',
      bg: 'bg-green-500/20',
      icon: 'text-green-400'
    };
  } else if (profit >= 100) {
    return {
      text: 'text-yellow-400',
      bg: 'bg-yellow-500/20',
      icon: 'text-yellow-400'
    };
  } else if (profit > 0) {
    return {
      text: 'text-blue-400',
      bg: 'bg-blue-500/20',
      icon: 'text-blue-400'
    };
  } else {
    return {
      text: 'text-red-400',
      bg: 'bg-red-500/20',
      icon: 'text-red-400'
    };
  }
}