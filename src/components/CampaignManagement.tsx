import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Target, Plus, Search, Calendar, Users, BarChart3, MoreVertical, Play, Pause } from 'lucide-react';

const CampaignManagement: React.FC = () => {
  const campaigns = [
    {
      id: 1,
      name: 'Workplace Wellbeing Study',
      startDate: '2024-01-01',
      endDate: '2024-03-31',
      status: 'Active',
      participants: 89,
      responses: 1247,
      responseRate: 78.5,
      description: 'Understanding workplace satisfaction and mental health patterns'
    },
    {
      id: 2,
      name: 'Student Mental Health Survey',
      startDate: '2024-01-15',
      endDate: '2024-04-15',
      status: 'Active',
      participants: 156,
      responses: 892,
      responseRate: 65.2,
      description: 'Tracking student wellbeing throughout the semester'
    },
    {
      id: 3,
      name: 'Remote Work Impact Study',
      startDate: '2023-11-01',
      endDate: '2024-01-31',
      status: 'Completed',
      participants: 45,
      responses: 980,
      responseRate: 85.1,
      description: 'Analyzing the effects of remote work on employee wellbeing'
    },
    {
      id: 4,
      name: 'Healthcare Workers Support',
      startDate: '2024-02-01',
      endDate: '2024-05-31',
      status: 'Scheduled',
      participants: 0,
      responses: 0,
      responseRate: 0,
      description: 'Supporting healthcare professionals through challenging times'
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Active':
        return 'bg-green-100 text-green-800';
      case 'Scheduled':
        return 'bg-blue-100 text-blue-800';
      case 'Completed':
        return 'bg-gray-100 text-gray-800';
      case 'Paused':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 space-x-4">
            <Link
              to="/admin"
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-2 rounded-xl">
                <Target className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Campaign Management</h1>
                <p className="text-sm text-gray-500">Manage survey campaigns</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions Bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0 mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">All Campaigns</h2>
            <p className="text-gray-600">{campaigns.length} total campaigns</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search campaigns..."
                className="pl-10 pr-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <button className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-2 rounded-xl font-semibold hover:from-purple-600 hover:to-pink-600 transition-all duration-300 flex items-center space-x-2">
              <Plus className="h-4 w-4" />
              <span>New Campaign</span>
            </button>
          </div>
        </div>

        {/* Campaigns Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-300 hover:-translate-y-1">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="text-xl font-semibold text-gray-900">{campaign.name}</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(campaign.status)}`}>
                      {campaign.status}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm mb-4">{campaign.description}</p>
                </div>
                <div className="flex items-center space-x-2">
                  {campaign.status === 'Active' && (
                    <button className="p-2 text-orange-500 hover:bg-orange-50 rounded-full transition-colors">
                      <Pause className="h-4 w-4" />
                    </button>
                  )}
                  {campaign.status === 'Scheduled' && (
                    <button className="p-2 text-green-500 hover:bg-green-50 rounded-full transition-colors">
                      <Play className="h-4 w-4" />
                    </button>
                  )}
                  <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors">
                    <MoreVertical className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center">
                  <div className="bg-blue-50 p-3 rounded-xl mb-2">
                    <Users className="h-6 w-6 text-blue-500 mx-auto" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{campaign.participants}</p>
                  <p className="text-sm text-gray-500">Participants</p>
                </div>
                <div className="text-center">
                  <div className="bg-green-50 p-3 rounded-xl mb-2">
                    <BarChart3 className="h-6 w-6 text-green-500 mx-auto" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{campaign.responses}</p>
                  <p className="text-sm text-gray-500">Responses</p>
                </div>
                <div className="text-center">
                  <div className="bg-purple-50 p-3 rounded-xl mb-2">
                    <Target className="h-6 w-6 text-purple-500 mx-auto" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{campaign.responseRate}%</p>
                  <p className="text-sm text-gray-500">Response Rate</p>
                </div>
              </div>

              <div className="flex items-center justify-between text-sm text-gray-500 mb-6">
                <div className="flex items-center space-x-1">
                  <Calendar className="h-4 w-4" />
                  <span>
                    {new Date(campaign.startDate).toLocaleDateString()} - {new Date(campaign.endDate).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <button className="flex-1 bg-gradient-to-r from-purple-50 to-pink-50 text-purple-600 hover:text-purple-800 py-2 px-4 rounded-xl font-medium transition-colors">
                  View Details
                </button>
                <button className="flex-1 bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-600 hover:text-blue-800 py-2 px-4 rounded-xl font-medium transition-colors">
                  Export Data
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CampaignManagement;