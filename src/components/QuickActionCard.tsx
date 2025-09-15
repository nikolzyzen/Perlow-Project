import React from 'react';
import { DivideIcon as LucideIcon } from 'lucide-react';

interface QuickActionCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  color: string;
  action: () => void;
}

const QuickActionCard: React.FC<QuickActionCardProps> = ({ title, description, icon: Icon, color, action }) => {
  return (
    <button
      onClick={action}
      className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-300 hover:-translate-y-1 text-left group"
    >
      <div className={`bg-gradient-to-r ${color} p-3 rounded-xl inline-flex mb-4 group-hover:scale-110 transition-transform duration-300`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </button>
  );
};

export default QuickActionCard;