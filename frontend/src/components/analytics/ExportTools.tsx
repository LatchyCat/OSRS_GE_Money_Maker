import React, { useState } from 'react';
import { Download, FileText, Image, Table, Share2, Copy, Check } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

export type ExportFormat = 'csv' | 'json' | 'png' | 'pdf';

export interface ExportData {
  items: any[];
  analytics: any;
  timeRange: string;
  filters: any;
  timestamp: Date;
}

interface ExportToolsProps {
  data: ExportData;
  onExport: (format: ExportFormat, options?: ExportOptions) => void;
  isExporting?: boolean;
}

interface ExportOptions {
  includeCharts?: boolean;
  includeAnalytics?: boolean;
  includeRawData?: boolean;
  customFilename?: string;
}

export const ExportTools: React.FC<ExportToolsProps> = ({
  data,
  onExport,
  isExporting = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('csv');
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    includeCharts: true,
    includeAnalytics: true,
    includeRawData: true,
    customFilename: ''
  });
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);

  const exportFormats = [
    {
      format: 'csv' as ExportFormat,
      label: 'CSV File',
      description: 'Spreadsheet compatible data',
      icon: Table,
      size: '~50KB'
    },
    {
      format: 'json' as ExportFormat,
      label: 'JSON File',
      description: 'Raw data with full details',
      icon: FileText,
      size: '~125KB'
    },
    {
      format: 'png' as ExportFormat,
      label: 'PNG Image',
      description: 'Chart screenshots',
      icon: Image,
      size: '~500KB'
    },
    {
      format: 'pdf' as ExportFormat,
      label: 'PDF Report',
      description: 'Complete analytics report',
      icon: FileText,
      size: '~1MB'
    }
  ];

  const handleExport = () => {
    const options = {
      ...exportOptions,
      customFilename: exportOptions.customFilename || `analytics-${data.timeRange}-${Date.now()}`
    };
    onExport(selectedFormat, options);
    setIsOpen(false);
  };

  const generateShareUrl = async () => {
    // In a real implementation, this would generate a shareable URL
    // For now, we'll create a mock URL
    const shareId = btoa(JSON.stringify({
      timestamp: data.timestamp.getTime(),
      timeRange: data.timeRange,
      itemCount: data.items.length
    }));
    
    const url = `${window.location.origin}/analytics/share/${shareId}`;
    setShareUrl(url);
  };

  const copyShareUrl = async () => {
    if (!shareUrl) {
      await generateShareUrl();
    }
    
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = shareUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const updateOption = <K extends keyof ExportOptions>(key: K, value: ExportOptions[K]) => {
    setExportOptions(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="relative">
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className="flex items-center gap-2"
      >
        <Download className="w-4 h-4" />
        {isExporting ? 'Exporting...' : 'Export'}
      </Button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 z-20">
          <Card className="p-6 min-w-96 shadow-xl border border-white/20">
            <div className="space-y-6">
              {/* Header */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">Export Analytics</h3>
                <div className="text-sm text-gray-400">
                  Export data from {data.timeRange} analysis ({data.items.length} items)
                </div>
              </div>

              {/* Format Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Export Format
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {exportFormats.map((format) => {
                    const Icon = format.icon;
                    return (
                      <button
                        key={format.format}
                        onClick={() => setSelectedFormat(format.format)}
                        className={`p-3 rounded-lg border transition-colors text-left ${
                          selectedFormat === format.format
                            ? 'bg-accent-500/20 border-accent-500/30 text-accent-400'
                            : 'bg-white/5 border-white/20 text-white hover:bg-white/10'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <Icon className="w-4 h-4" />
                          <span className="font-medium text-sm">{format.label}</span>
                        </div>
                        <div className="text-xs text-gray-400 mb-1">
                          {format.description}
                        </div>
                        <Badge variant="secondary" size="sm">
                          {format.size}
                        </Badge>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Export Options */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Include in Export
                </label>
                <div className="space-y-2">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={exportOptions.includeCharts}
                      onChange={(e) => updateOption('includeCharts', e.target.checked)}
                      className="w-4 h-4 text-accent-400 border-gray-600 rounded focus:ring-accent-400"
                    />
                    <span className="text-sm text-gray-300">Charts and visualizations</span>
                  </label>
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={exportOptions.includeAnalytics}
                      onChange={(e) => updateOption('includeAnalytics', e.target.checked)}
                      className="w-4 h-4 text-accent-400 border-gray-600 rounded focus:ring-accent-400"
                    />
                    <span className="text-sm text-gray-300">Analytics and insights</span>
                  </label>
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={exportOptions.includeRawData}
                      onChange={(e) => updateOption('includeRawData', e.target.checked)}
                      className="w-4 h-4 text-accent-400 border-gray-600 rounded focus:ring-accent-400"
                    />
                    <span className="text-sm text-gray-300">Raw data tables</span>
                  </label>
                </div>
              </div>

              {/* Custom Filename */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Custom Filename (optional)
                </label>
                <input
                  type="text"
                  placeholder={`analytics-${data.timeRange}-${Date.now()}`}
                  value={exportOptions.customFilename}
                  onChange={(e) => updateOption('customFilename', e.target.value)}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:border-accent-400 focus:outline-none"
                />
              </div>

              {/* Export Actions */}
              <div className="space-y-3">
                <Button
                  variant="primary"
                  onClick={handleExport}
                  disabled={isExporting}
                  className="w-full flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  {isExporting ? 'Exporting...' : `Export as ${selectedFormat.toUpperCase()}`}
                </Button>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-white/20" />
                  </div>
                  <div className="relative flex justify-center text-xs">
                    <span className="bg-gray-800 px-2 text-gray-400">or</span>
                  </div>
                </div>

                <Button
                  variant="outline"
                  onClick={copyShareUrl}
                  className="w-full flex items-center justify-center gap-2"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4" />
                      URL Copied!
                    </>
                  ) : (
                    <>
                      <Share2 className="w-4 h-4" />
                      Share Analytics Link
                    </>
                  )}
                </Button>

                {shareUrl && (
                  <div className="p-3 bg-white/5 rounded-lg">
                    <div className="text-xs text-gray-400 mb-1">Share URL:</div>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 text-xs text-accent-400 truncate">
                        {shareUrl}
                      </code>
                      <button
                        onClick={copyShareUrl}
                        className="text-gray-400 hover:text-white"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Export Info */}
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                <div className="text-sm text-blue-400 font-medium mb-1">Export Details</div>
                <div className="text-xs text-gray-300 space-y-0.5">
                  <div>• {data.items.length} items included</div>
                  <div>• Time range: {data.timeRange}</div>
                  <div>• Generated: {data.timestamp.toLocaleString()}</div>
                  <div>• Format: {exportFormats.find(f => f.format === selectedFormat)?.label}</div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-10" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};