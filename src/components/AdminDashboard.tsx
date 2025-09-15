import React, { useState, useEffect } from 'react';
import { Users, MessageSquare, Target, TrendingUp, Plus, Send, Settings, BarChart3, UserPlus, Calendar } from 'lucide-react';
import { Link } from 'react-router-dom';
import StatsCard from './StatsCard';
import QuickActionCard from './QuickActionCard';
import RecentActivity from './RecentActivity';

interface Stats {
  totalUsers: number;
  activeUsers: number;
  totalCampaigns: number;
  totalResponses: number;
  responseRate: number;
  avgWellbeingScore: number;
}

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats>({
    totalUsers: 142,
    activeUsers: 89,
    totalCampaigns: 8,
    totalResponses: 1247,
    responseRate: 78.5,
    avgWellbeingScore: 7.3
  });

  const [loading, setLoading] = useState(false);

  // Fetch data from API
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/stats');
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const quickActions = [
    {
      title: 'Send Test SMS',
      description: 'Send a test survey to verify setup',
      icon: Send,
      color: 'from-blue-500 to-blue-600',
      action: () => console.log('Send test SMS')
    },
    {
      title: 'Add New User',
      description: 'Register a new participant',
      icon: UserPlus,
      color: 'from-green-500 to-green-600',
      action: () => console.log('Add user')
    },
    {
      title: 'Create Campaign',
      description: 'Launch a new survey campaign',
      icon: Calendar,
      color: 'from-purple-500 to-purple-600',
      action: () => console.log('Create campaign')
    },
    {
      title: 'View Analytics',
      description: 'Deep dive into response data',
      icon: BarChart3,
      color: 'from-orange-500 to-orange-600',
      action: () => console.log('View analytics')
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-r from-purple-500 to-blue-500 p-2 rounded-xl">
                <MessageSquare className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">SMS Survey</h1>
                <p className="text-sm text-gray-500">Wellbeing Analytics Platform</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors">
                <Settings className="h-5 w-5" />
              </button>
              <div className="h-8 w-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">A</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Good morning, Admin! 👋</h2>
          <p className="text-gray-600">Here's what's happening with your surveys today.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 mb-8">
          <StatsCard
            title="Total Users"
            value={stats.totalUsers}
            change="+12%"
            trend="up"
            icon={Users}
            color="from-blue-500 to-blue-600"
          />
          <StatsCard
            title="Active Users"
            value={stats.activeUsers}
            change="+8%"
            trend="up"
            icon={TrendingUp}
            color="from-green-500 to-green-600"
          />
          <StatsCard
            title="Campaigns"
            value={stats.totalCampaigns}
            change="+2"
            trend="up"
            icon={Target}
            color="from-purple-500 to-purple-600"
          />
          <StatsCard
            title="Responses"
            value={stats.totalResponses}
            change="+156"
            trend="up"
            icon={MessageSquare}
            color="from-orange-500 to-orange-600"
          />
          <StatsCard
            title="Response Rate"
            value={`${stats.responseRate}%`}
            change="+3.2%"
            trend="up"
            icon={BarChart3}
            color="from-teal-500 to-teal-600"
          />
          <StatsCard
            title="Avg Wellbeing"
            value={`${stats.avgWellbeingScore}/10`}
            change="+0.4"
            trend="up"
            icon={TrendingUp}
            color="from-pink-500 to-pink-600"
          />
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h3 className="text-xl font-semibold text-gray-900 mb-6">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {quickActions.map((action, index) => (
              <QuickActionCard key={index} {...action} />
            ))}
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Activity */}
          <div className="lg:col-span-2">
            <RecentActivity />
          </div>

          {/* Navigation Menu */}
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">System Management</h3>
              <nav className="space-y-2">
                <Link
                  to="/users"
                  className="flex items-center space-x-3 p-3 rounded-xl hover:bg-gray-50 transition-colors group"
                >
                  <Users className="h-5 w-5 text-gray-400 group-hover:text-blue-500" />
                  <span className="text-gray-700 group-hover:text-gray-900">User Management</span>
                </Link>
                <Link
                  to="/campaigns"
                  className="flex items-center space-x-3 p-3 rounded-xl hover:bg-gray-50 transition-colors group"
                >
                  <Target className="h-5 w-5 text-gray-400 group-hover:text-purple-500" />
                  <span className="text-gray-700 group-hover:text-gray-900">Campaign Management</span>
                </Link>
                <Link
                  to="/responses"
                  className="flex items-center space-x-3 p-3 rounded-xl hover:bg-gray-50 transition-colors group"
                >
                  <MessageSquare className="h-5 w-5 text-gray-400 group-hover:text-green-500" />
                  <span className="text-gray-700 group-hover:text-gray-900">View Responses</span>
                </Link>
                <Link
                  to="/analytics/1/1"
                  className="flex items-center space-x-3 p-3 rounded-xl hover:bg-gray-50 transition-colors group"
                >
                  <BarChart3 className="h-5 w-5 text-gray-400 group-hover:text-orange-500" />
                  <span className="text-gray-700 group-hover:text-gray-900">Personal Analytics</span>
                </Link>
              </nav>
            </div>

            {/* System Status */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">SMS Service</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span className="text-sm text-green-600">Active</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Database</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span className="text-sm text-green-600">Connected</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Scheduler</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span className="text-sm text-green-600">Running</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;