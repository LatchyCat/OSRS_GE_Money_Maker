import React, { useState } from 'react';
import { Filter, X, Search, SlidersHorizontal } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

export interface FilterOptions {
  search: string;
  profitRange: { min: number; max: number };
  volumeCategory: 'all' | 'low' | 'medium' | 'high';
  riskLevel: 'all' | 'low' | 'medium' | 'high';
  itemCategories: string[];
  sortBy: 'profit' | 'volume' | 'name' | 'risk';
  sortOrder: 'asc' | 'desc';
}

interface FilterControlsProps {
  filters: FilterOptions;
  onFiltersChange: (filters: FilterOptions) => void;
  availableCategories?: string[];
  totalItems?: number;
  filteredItems?: number;
}

export const FilterControls: React.FC<FilterControlsProps> = ({
  filters,
  onFiltersChange,
  availableCategories = [],
  totalItems = 0,
  filteredItems = 0
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const updateFilter = <K extends keyof FilterOptions>(key: K, value: FilterOptions[K]) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const clearAllFilters = () => {
    onFiltersChange({
      search: '',
      profitRange: { min: 0, max: 10000 },
      volumeCategory: 'all',
      riskLevel: 'all',
      itemCategories: [],
      sortBy: 'profit',
      sortOrder: 'desc'
    });
  };

  const getActiveFilterCount = () => {
    let count = 0;
    if (filters.search) count++;
    if (filters.profitRange.min > 0 || filters.profitRange.max < 10000) count++;
    if (filters.volumeCategory !== 'all') count++;
    if (filters.riskLevel !== 'all') count++;
    if (filters.itemCategories.length > 0) count++;
    return count;
  };

  const activeFilterCount = getActiveFilterCount();

  const volumeOptions = [
    { value: 'all', label: 'All Volumes' },
    { value: 'low', label: 'Low Volume' },
    { value: 'medium', label: 'Medium Volume' },
    { value: 'high', label: 'High Volume' }
  ];

  const riskOptions = [
    { value: 'all', label: 'All Risk Levels' },
    { value: 'low', label: 'Low Risk' },
    { value: 'medium', label: 'Medium Risk' },
    { value: 'high', label: 'High Risk' }
  ];

  const sortOptions = [
    { value: 'profit', label: 'Profit' },
    { value: 'volume', label: 'Volume' },
    { value: 'name', label: 'Name' },
    { value: 'risk', label: 'Risk Level' }
  ];

  const toggleCategory = (category: string) => {
    const updatedCategories = filters.itemCategories.includes(category)
      ? filters.itemCategories.filter(c => c !== category)
      : [...filters.itemCategories, category];
    updateFilter('itemCategories', updatedCategories);
  };

  return (
    <div className="space-y-4">
      {/* Filter Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2"
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>Filters</span>
            {activeFilterCount > 0 && (
              <Badge variant="accent" size="sm">
                {activeFilterCount}
              </Badge>
            )}
          </Button>

          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4 mr-1" />
              Clear All
            </Button>
          )}
        </div>

        <div className="text-sm text-gray-400">
          Showing {filteredItems} of {totalItems} items
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search items..."
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:border-accent-400 focus:outline-none"
        />
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <Card className="p-6 space-y-6">
          {/* Profit Range */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Profit Range (GP)
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.profitRange.min}
                  onChange={(e) => updateFilter('profitRange', {
                    ...filters.profitRange,
                    min: parseInt(e.target.value) || 0
                  })}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:border-accent-400 focus:outline-none"
                />
              </div>
              <div>
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.profitRange.max}
                  onChange={(e) => updateFilter('profitRange', {
                    ...filters.profitRange,
                    max: parseInt(e.target.value) || 10000
                  })}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:border-accent-400 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Volume Category */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Volume Category
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {volumeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => updateFilter('volumeCategory', option.value as any)}
                  className={`p-2 rounded-lg text-sm font-medium transition-colors ${
                    filters.volumeCategory === option.value
                      ? 'bg-accent-500/20 border border-accent-500/30 text-accent-400'
                      : 'bg-white/10 border border-white/20 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Risk Level */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Risk Level
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {riskOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => updateFilter('riskLevel', option.value as any)}
                  className={`p-2 rounded-lg text-sm font-medium transition-colors ${
                    filters.riskLevel === option.value
                      ? 'bg-accent-500/20 border border-accent-500/30 text-accent-400'
                      : 'bg-white/10 border border-white/20 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Item Categories */}
          {availableCategories.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Item Categories
              </label>
              <div className="flex flex-wrap gap-2">
                {availableCategories.map((category) => (
                  <button
                    key={category}
                    onClick={() => toggleCategory(category)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      filters.itemCategories.includes(category)
                        ? 'bg-accent-500/20 border border-accent-500/30 text-accent-400'
                        : 'bg-white/10 border border-white/20 text-gray-300 hover:bg-white/20'
                    }`}
                  >
                    {category}
                    {filters.itemCategories.includes(category) && (
                      <X className="w-3 h-3 ml-1 inline" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Sort Options */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Sort By
              </label>
              <select
                value={filters.sortBy}
                onChange={(e) => updateFilter('sortBy', e.target.value as any)}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white focus:border-accent-400 focus:outline-none"
              >
                {sortOptions.map((option) => (
                  <option key={option.value} value={option.value} className="bg-gray-800">
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Sort Order
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => updateFilter('sortOrder', 'desc')}
                  className={`p-2 rounded-lg text-sm font-medium transition-colors ${
                    filters.sortOrder === 'desc'
                      ? 'bg-accent-500/20 border border-accent-500/30 text-accent-400'
                      : 'bg-white/10 border border-white/20 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  High to Low
                </button>
                <button
                  onClick={() => updateFilter('sortOrder', 'asc')}
                  className={`p-2 rounded-lg text-sm font-medium transition-colors ${
                    filters.sortOrder === 'asc'
                      ? 'bg-accent-500/20 border border-accent-500/30 text-accent-400'
                      : 'bg-white/10 border border-white/20 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  Low to High
                </button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.search && (
            <Badge variant="secondary" className="flex items-center gap-1">
              Search: {filters.search}
              <button
                onClick={() => updateFilter('search', '')}
                className="ml-1 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          )}

          {(filters.profitRange.min > 0 || filters.profitRange.max < 10000) && (
            <Badge variant="secondary" className="flex items-center gap-1">
              Profit: {filters.profitRange.min}-{filters.profitRange.max} GP
              <button
                onClick={() => updateFilter('profitRange', { min: 0, max: 10000 })}
                className="ml-1 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          )}

          {filters.volumeCategory !== 'all' && (
            <Badge variant="secondary" className="flex items-center gap-1">
              Volume: {filters.volumeCategory}
              <button
                onClick={() => updateFilter('volumeCategory', 'all')}
                className="ml-1 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          )}

          {filters.riskLevel !== 'all' && (
            <Badge variant="secondary" className="flex items-center gap-1">
              Risk: {filters.riskLevel}
              <button
                onClick={() => updateFilter('riskLevel', 'all')}
                className="ml-1 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          )}

          {filters.itemCategories.map((category) => (
            <Badge key={category} variant="secondary" className="flex items-center gap-1">
              {category}
              <button
                onClick={() => toggleCategory(category)}
                className="ml-1 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};