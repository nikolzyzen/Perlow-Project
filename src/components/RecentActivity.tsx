import React from 'react';
import { MessageSquare, User, Target, Clock } from 'lucide-react';

const RecentActivity: React.FC = () => {
  const activities = [
    {
      id: 1,
      type: 'response',
      user: 'Sarah Johnson',
      action: 'Completed daily survey',
      time: '2 minutes ago',
      icon: MessageSquare,
      color: 'from-blue-500 to-blue-600',
      scores: { joy: 8, achievement: 7, meaningfulness: 9 }
    },
    {
      id: 2,
      type: 'user',
      user: 'New User',
      action: 'Registered for campaign',
      time: '15 minutes ago',
      icon: User,
      color: 'from-green-500 to-green-600'
    },
    {
      id: 3,
      type: 'campaign',
      user: 'System',
      action: 'Started "Workplace Wellbeing" campaign',
      time: '1 hour ago',
      icon: Target,
      color: 'from-purple-500 to-purple-600'
    },
    {
      id: 4,
      type: 'response',
      user: 'Mike Chen',
      action: 'Completed daily survey',
      time: '2 hours ago',
      icon: MessageSquare,
      color: 'from-blue-500 to-blue-600',
      scores: { joy: 6, achievement: 8, meaningfulness: 7 }
    },
    {
      id: 5,
      type: 'system',
      user: 'System',
      action: 'Sent daily surveys to 89 users',
      time: '3 hours ago',
      icon: Clock,
      color: 'from-orange-500 to-orange-600'
    }
  ];

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">Recent Activity</h3>
      <div className="space-y-4">
        {activities.map((activity) => (
          <div key={activity.id} className="flex items-start space-x-4 p-4 rounded-xl hover:bg-gray-50 transition-colors">
            <div className={`bg-gradient-to-r ${activity.color} p-2 rounded-lg flex-shrink-0`}>
              <activity.icon className="h-4 w-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">{activity.user}</p>
              <p className="text-sm text-gray-600">{activity.action}</p>
              {activity.scores && (
                <div className="flex items-center space-x-4 mt-2">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                    <span className="text-xs text-gray-500">Joy: {activity.scores.joy}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span className="text-xs text-gray-500">Achievement: {activity.scores.achievement}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                    <span className="text-xs text-gray-500">Meaningfulness: {activity.scores.meaningfulness}</span>
                  </div>
                </div>
              )}
            </div>
            <div className="text-xs text-gray-500 flex-shrink-0">
              {activity.time}
            </div>
          </div>
        ))}
      </div>
      <button className="w-full mt-4 text-sm text-blue-600 hover:text-blue-800 font-medium">
        View all activity
      </button>
    </div>
  );
};

export default RecentActivity;