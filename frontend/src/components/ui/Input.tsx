import React from 'react';
import { Search } from 'lucide-react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
  wrapperClassName?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  icon,
  className = '',
  wrapperClassName = '',
  ...props
}) => {
  return (
    <div className={`space-y-2 ${wrapperClassName}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-200">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-400 text-sm">{icon}</span>
          </div>
        )}
        <input
          className={`input-glass w-full ${icon ? 'pl-10' : ''} ${error ? 'ring-2 ring-red-500' : ''} ${className}`}
          {...props}
        />
      </div>
      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}
    </div>
  );
};

export const SearchInput: React.FC<Omit<InputProps, 'icon'>> = (props) => {
  return <Input icon={<Search className="w-4 h-4" />} {...props} />;
};