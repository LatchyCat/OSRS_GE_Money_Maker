import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, Grid, List, SortAsc } from 'lucide-react';
import { itemsApi } from '../api/itemsApi';
import { ItemCard } from '../components/features/ItemCard';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input, SearchInput } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import type { Item, ItemFilters, ViewMode, SortOption } from '../types';

export const Items: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortBy, setSortBy] = useState<SortOption>('profit');
  const [filters, setFilters] = useState({
    members: undefined as boolean | undefined,
    minProfit: '',
    maxProfit: '',
    minMargin: '',
    maxMargin: ''
  });
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);

  const buildApiFilters = useMemo((): ItemFilters => {
    const apiFilters: ItemFilters = {
      page: currentPage,
      ordering: sortBy === 'profit' ? '-current_profit' : 
                sortBy === 'margin' ? '-current_profit_margin' :
                sortBy === 'recommendation' ? '-recommendation_score' : 'name'
    };

    if (searchQuery.trim()) {
      apiFilters.search = searchQuery.trim();
    }

    if (filters.members !== undefined) {
      apiFilters.members = filters.members;
    }

    if (filters.minProfit) {
      apiFilters.min_profit = parseInt(filters.minProfit);
    }

    if (filters.maxProfit) {
      apiFilters.max_profit = parseInt(filters.maxProfit);
    }

    if (filters.minMargin) {
      apiFilters.min_margin = parseFloat(filters.minMargin);
    }

    if (filters.maxMargin) {
      apiFilters.max_margin = parseFloat(filters.maxMargin);
    }

    return apiFilters;
  }, [searchQuery, filters, sortBy, currentPage]);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const result = await itemsApi.getItems(buildApiFilters);
      setItems(result.results);
      setTotalCount(result.count);
      setHasNext(!!result.next);
    } catch (error) {
      console.error('Error fetching items:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [buildApiFilters]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1); // Reset to first page when searching
  };

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const clearFilters = () => {
    setFilters({
      members: undefined,
      minProfit: '',
      maxProfit: '',
      minMargin: '',
      maxMargin: ''
    });
    setSearchQuery('');
    setCurrentPage(1);
  };

  const getActiveFilterCount = () => {
    let count = 0;
    if (filters.members !== undefined) count++;
    if (filters.minProfit) count++;
    if (filters.maxProfit) count++;
    if (filters.minMargin) count++;
    if (filters.maxMargin) count++;
    return count;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-white">Items</h1>
          <p className="text-gray-400 mt-2">
            {totalCount.toLocaleString()} OSRS items tracked
          </p>
        </div>

        {/* View Controls */}
        <div className="flex items-center space-x-2">
          <Button
            variant={viewMode === 'grid' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="w-4 h-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="w-4 h-4" />
          </Button>
        </div>
      </motion.div>

      {/* Search and Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="space-y-4"
      >
        {/* Search Bar */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <SearchInput
              placeholder="Search items by name..."
              value={searchQuery}
              onChange={handleSearch}
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="secondary"
              onClick={() => setFiltersOpen(!filtersOpen)}
              icon={<Filter className="w-4 h-4" />}
            >
              Filters
              {getActiveFilterCount() > 0 && (
                <Badge variant="info" size="sm" className="ml-2">
                  {getActiveFilterCount()}
                </Badge>
              )}
            </Button>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="input-glass text-sm"
            >
              <option value="profit">Sort by Profit</option>
              <option value="margin">Sort by Margin</option>
              <option value="recommendation">Sort by Recommendation</option>
              <option value="name">Sort by Name</option>
            </select>
          </div>
        </div>

        {/* Filters Panel */}
        {filtersOpen && (
          <Card className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Filters</h3>
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear All
              </Button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-200 mb-2">
                  Membership
                </label>
                <select
                  value={filters.members === undefined ? '' : filters.members.toString()}
                  onChange={(e) => 
                    handleFilterChange('members', e.target.value === '' ? undefined : e.target.value === 'true')
                  }
                  className="input-glass w-full text-sm"
                >
                  <option value="">All Items</option>
                  <option value="false">Free-to-Play</option>
                  <option value="true">Members Only</option>
                </select>
              </div>

              <Input
                label="Min Profit (GP)"
                value={filters.minProfit}
                onChange={(e) => handleFilterChange('minProfit', e.target.value)}
                placeholder="0"
                type="number"
              />

              <Input
                label="Max Profit (GP)"
                value={filters.maxProfit}
                onChange={(e) => handleFilterChange('maxProfit', e.target.value)}
                placeholder="10000"
                type="number"
              />

              <Input
                label="Min Margin (%)"
                value={filters.minMargin}
                onChange={(e) => handleFilterChange('minMargin', e.target.value)}
                placeholder="0"
                type="number"
                step="0.1"
              />

              <Input
                label="Max Margin (%)"
                value={filters.maxMargin}
                onChange={(e) => handleFilterChange('maxMargin', e.target.value)}
                placeholder="100"
                type="number"
                step="0.1"
              />
            </div>
          </Card>
        )}
      </motion.div>

      {/* Items Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="Loading items..." />
          </div>
        ) : items.length === 0 ? (
          <Card className="text-center py-12">
            <div className="space-y-4">
              <Search className="w-16 h-16 text-gray-400 mx-auto" />
              <div>
                <h3 className="text-lg font-semibold text-white">No items found</h3>
                <p className="text-gray-400 mt-2">
                  Try adjusting your search criteria or filters
                </p>
              </div>
              <Button variant="secondary" onClick={clearFilters}>
                Clear Filters
              </Button>
            </div>
          </Card>
        ) : (
          <div className={
            viewMode === 'grid' 
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 items-stretch'
              : 'space-y-4'
          }>
            {items.map((item, index) => (
              <motion.div
                key={item.item_id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.05 * index }}
                className={viewMode === 'grid' ? 'flex' : ''}
              >
                <ItemCard 
                  item={item} 
                  onClick={() => navigate(`/items/${item.item_id}`)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Pagination */}
      {!loading && items.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex justify-center space-x-2"
        >
          <Button
            variant="secondary"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage(prev => prev - 1)}
          >
            Previous
          </Button>
          <div className="flex items-center space-x-2">
            <span className="text-gray-400">
              Page {currentPage}
            </span>
          </div>
          <Button
            variant="secondary"
            disabled={!hasNext}
            onClick={() => setCurrentPage(prev => prev + 1)}
          >
            Next
          </Button>
        </motion.div>
      )}
    </div>
  );
};