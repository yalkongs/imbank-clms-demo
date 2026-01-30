import React, { useEffect } from 'react';
import { X, HelpCircle, Info } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export default function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl'
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal Panel */}
        <div className={`inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle ${sizeClasses[size]} w-full`}>
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center">
              <Info className="text-blue-600 mr-2" size={20} />
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-200"
            >
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
            {children}
          </div>

          {/* Footer */}
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
            >
              닫기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Feature Description Modal with Markdown-like rendering
interface FeatureModalProps {
  isOpen: boolean;
  onClose: () => void;
  feature: {
    title: string;
    description?: string;
    benefits?: string[];
    methodology?: string;
    formula?: string;
  } | null;
}

export function FeatureModal({ isOpen, onClose, feature }: FeatureModalProps) {
  if (!feature) return null;

  // Simple markdown-like parsing
  const renderMethodology = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, i) => {
      // Headers
      if (line.startsWith('**') && line.endsWith('**')) {
        return <h4 key={i} className="text-sm font-bold text-gray-900 mt-4 mb-2">{line.replace(/\*\*/g, '')}</h4>;
      }
      // Code blocks
      if (line.startsWith('```')) {
        return null;
      }
      // List items
      if (line.startsWith('- ')) {
        return <li key={i} className="text-sm text-gray-700 ml-4">{line.substring(2)}</li>;
      }
      if (line.match(/^\d+\./)) {
        return <li key={i} className="text-sm text-gray-700 ml-4">{line.substring(line.indexOf('.') + 2)}</li>;
      }
      // Table rows
      if (line.startsWith('|')) {
        const cells = line.split('|').filter(c => c.trim());
        if (cells.every(c => c.trim().match(/^-+$/))) return null;
        return (
          <div key={i} className="flex text-xs">
            {cells.map((cell, j) => (
              <span key={j} className="flex-1 px-2 py-1 border-b border-gray-200">{cell.trim()}</span>
            ))}
          </div>
        );
      }
      // Code line
      if (line.includes('=') && !line.includes(':')) {
        return <code key={i} className="block text-xs bg-gray-100 px-2 py-1 rounded font-mono my-1">{line}</code>;
      }
      // Regular text
      if (line.trim()) {
        return <p key={i} className="text-sm text-gray-700 my-1">{line}</p>;
      }
      return null;
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={feature.title} size="lg">
      <div className="space-y-4">
        {feature.description && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">{feature.description}</p>
          </div>
        )}

        {feature.benefits && feature.benefits.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">주요 이점</h4>
            <ul className="list-disc list-inside space-y-1">
              {feature.benefits.map((benefit, i) => (
                <li key={i} className="text-sm text-gray-700">{benefit}</li>
              ))}
            </ul>
          </div>
        )}

        {feature.methodology && (
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">방법론</h4>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              {renderMethodology(feature.methodology)}
            </div>
          </div>
        )}

        {feature.formula && (
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">핵심 수식</h4>
            <code className="block bg-gray-900 text-green-400 p-4 rounded-lg text-sm font-mono">
              {feature.formula}
            </code>
          </div>
        )}
      </div>
    </Modal>
  );
}

// Help Button Component
interface HelpButtonProps {
  onClick: () => void;
  size?: 'sm' | 'md';
}

export function HelpButton({ onClick, size = 'md' }: HelpButtonProps) {
  const sizeClass = size === 'sm' ? 'w-5 h-5' : 'w-6 h-6';
  return (
    <button
      onClick={onClick}
      className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
      title="기능 설명 보기"
    >
      <HelpCircle className={sizeClass} />
    </button>
  );
}
