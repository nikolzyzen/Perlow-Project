import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, MessageSquare, Filter, Download, Search, Calendar, User, Heart, Target, Star } from 'lucide-react';

const ResponsesView: React.FC = () => {
  const responses = [
    {
      id: 1,
      userName: 'Sarah Johnson',
      userPhone: '+1 (555) 123-4567',
      date: '2024-01-15',
      time: '14:32',
      joy: 9,
      achievement: 8,
      meaningfulness: 9,
      influence: 'Had a great team meeting and completed a major project milestone',
      campaign: 'Workplace Wellbeing Study'
    },
    {
      id: 2,
      userName: 'Mike Chen',
      userPhone: '+1 (555) 234-5678',
      date: '2024-01-15',
      time: '09:15',
      joy: 7,
      achievement: 9,
      meaningfulness: 8,
      influence: 'Finished an important presentation and received positive feedback',
      campaign: 'Workplace Wellbeing Study'
    },
    {
      id: 3,
      userName: 'Emily Rodriguez',
      userPhone: '+1 (555) 345-6789',
      date: '2024-01-14',
      time: '20:45',
      joy: 8,
      achievement: 6,
      meaningfulness: 9,
      influence: 'Spent quality time with family, work was a bit slow today',
      campaign: 'Student Mental Health Survey'
    },
    {
      id: 4,
      userName: 'David Kim',
      userPhone: '+1 (555) 456-7890',
      date: '2024-01-14',
      time: '18:22',
      joy: 6,
      achievement: 8,
      meaningfulness: 7,
      influence: 'Busy day at work but accomplished several tasks',
      campaign: 'Remote Work Impact Study'
    }
  ];

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-100';
    if (score >= 6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-green-50">
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
              <div className="bg-gradient-to-r from-green-500 to-teal-500 p-2 rounded-xl">
                <MessageSquare className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Survey Responses</h1>
                <p className="text-sm text-gray-500">View and analyze participant responses</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions Bar */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center space-y-4 lg:space-y-0 mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">All Responses</h2>
            <p className="text-gray-600">{responses.length} recent responses</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search responses..."
                className="pl-10 pr-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            </div>
            <button className="flex items-center space-x-2 px-4 py-2 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-gray-700">Filter</span>
            </button>
            <button className="bg-gradient-to-r from-green-500 to-teal-500 text-white px-6 py-2 rounded-xl font-semibold hover:from-green-600 hover:to-teal-600 transition-all duration-300 flex items-center space-x-2">
              <Download className="h-4 w-4" />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Responses List */}
        <div className="space-y-6">
          {responses.map((response) => (
            <div key={response.id} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-300">
              <div className="flex flex-col lg:flex-row lg:items-start lg:space-x-6">
                {/* User Info */}
                <div className="flex items-center space-x-4 mb-4 lg:mb-0 lg:w-64">
                  <div className="w-12 h-12 bg-gradient-to-r from-green-400 to-teal-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-white font-semibold">
                      {response.userName.split(' ').map(n => n[0]).join('')}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{response.userName}</h3>
                    <p className="text-sm text-gray-500">{response.userPhone}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Calendar className="h-3 w-3 text-gray-400" />
                      <span className="text-xs text-gray-500">
                        {new Date(response.date).toLocaleDateString()} at {response.time}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Scores */}
                <div className="flex-1">
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="text-center">
                      <div className="bg-pink-50 p-3 rounded-xl mb-2">
                        <Heart className="h-5 w-5 text-pink-500 mx-auto" />
                      </div>
                      <div className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${getScoreColor(response.joy)}`}>
                        {response.joy}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Joy</p>
                    </div>
                    <div className="text-center">
                      <div className="bg-blue-50 p-3 rounded-xl mb-2">
                        <Target className="h-5 w-5 text-blue-500 mx-auto" />
                      </div>
                      <div className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${getScoreColor(response.achievement)}`}>
                        {response.achievement}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Achievement</p>
                    </div>
                    <div className="text-center">
                      <div className="bg-purple-50 p-3 rounded-xl mb-2">
                        <Star className="h-5 w-5 text-purple-500 mx-auto" />
                      </div>
                      <div className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${getScoreColor(response.meaningfulness)}`}>
                        {response.meaningfulness}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Meaningfulness</p>
                    </div>
                  </div>

                  {/* Influence Text */}
                  <div className="bg-gray-50 rounded-xl p-4 mb-3">
                    <p className="text-gray-700 italic text-sm">"{response.influence}"</p>
                  </div>

                  {/* Campaign Tag */}
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {response.campaign}
                    </span>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        Overall: {((response.joy + response.achievement + response.meaningfulness) / 3).toFixed(1)}/10
                      </p>
                      <div className="w-16 bg-gray-200 rounded-full h-1.5 mt-1">
                        <div 
                          className="bg-gradient-to-r from-green-400 to-blue-500 h-1.5 rounded-full"
                          style={{ width: `${((response.joy + response.achievement + response.meaningfulness) / 30) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Load More */}
        <div className="text-center mt-12">
          <button className="bg-white border border-gray-200 text-gray-700 px-8 py-3 rounded-xl font-medium hover:bg-gray-50 hover:border-gray-300 transition-all duration-300">
            Load More Responses
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResponsesView;