import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, TrendingUp, Heart, Target, Star, Calendar, Award, MessageSquare } from 'lucide-react';

interface AnalyticsData {
  user: {
    id: number;
    name: string;
    phoneNumber: string;
  };
  campaign: {
    id: number;
    name: string;
  };
  responses: Array<{
    id: number;
    joyRating: number;
    achievementRating: number;
    meaningfulnessRating: number;
    influenceText: string;
    submittedAt: string;
    surveyDate: string;
  }>;
  analytics: {
    avgJoy: number;
    avgAchievement: number;
    avgMeaningfulness: number;
    totalResponses: number;
  };
}

const PersonalAnalytics: React.FC = () => {
  const { userId, campaignId } = useParams();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/analytics/${userId}/${campaignId}`);
        if (response.ok) {
          const analyticsData = await response.json();
          setData(analyticsData);
        }
      } catch (error) {
        console.error('Error fetching analytics:', error);
      } finally {
        setLoading(false);
      }
    };

    if (userId && campaignId) {
      fetchAnalytics();
    }
  }, [userId, campaignId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your analytics...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No data available</p>
        </div>
      </div>
    );
  }

  const userData = {
    name: data.user.name,
    phone: data.user.phoneNumber,
    totalResponses: data.analytics.totalResponses,
    avgJoy: data.analytics.avgJoy,
    avgAchievement: data.analytics.avgAchievement,
    avgMeaningfulness: data.analytics.avgMeaningfulness,
    overallScore: (data.analytics.avgJoy + data.analytics.avgAchievement + data.analytics.avgMeaningfulness) / 3,
    bestDay: 'Tuesday',
    improvementArea: 'Achievement',
    streak: 14
  };

  const responses = data.responses.slice(0, 10).map(response => ({
    date: response.surveyDate,
    joy: response.joyRating,
    achievement: response.achievementRating,
    meaningfulness: response.meaningfulnessRating,
    influence: response.influenceText || 'No additional notes'
  }));

  // Determine strongest and weakest areas
  const strongestArea = userData.avgJoy >= userData.avgAchievement && userData.avgJoy >= userData.avgMeaningfulness 
    ? 'Joy' 
    : userData.avgAchievement >= userData.avgMeaningfulness 
    ? 'Achievement' 
    : 'Meaningfulness';
  
  const weakestArea = userData.avgJoy <= userData.avgAchievement && userData.avgJoy <= userData.avgMeaningfulness 
    ? 'Joy' 
    : userData.avgAchievement <= userData.avgMeaningfulness 
    ? 'Achievement' 
    : 'Meaningfulness';

  const insights = [
    {
      title: 'Your Superpower',
      description: `${strongestArea} is your strongest area at ${strongestArea === 'Joy' ? userData.avgJoy : strongestArea === 'Achievement' ? userData.avgAchievement : userData.avgMeaningfulness}/10. You consistently excel in this area!`,
      icon: Star,
      color: 'from-yellow-400 to-orange-500',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-800'
    },
    {
      title: 'Growth Opportunity',
      description: `${weakestArea} shows room for growth at ${weakestArea === 'Joy' ? userData.avgJoy : weakestArea === 'Achievement' ? userData.avgAchievement : userData.avgMeaningfulness}/10. Consider setting smaller, daily wins to boost this score.`,
      icon: Target,
      color: 'from-blue-400 to-blue-600',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-800'
    },
    {
      title: 'Consistency Champion',
      description: `You've submitted ${userData.totalResponses} responses! Your commitment to self-reflection is inspiring.`,
      icon: Award,
      color: 'from-green-400 to-green-600',
      bgColor: 'bg-green-50',
      textColor: 'text-green-800'
    }
  ];

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 8) return 'bg-green-100';
    if (score >= 6) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-indigo-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 space-x-4">
            <Link
              to="/admin"
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Personal Analytics</h1>
              <p className="text-sm text-gray-500">Wellbeing insights for {userData.name}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full mb-6">
            <span className="text-2xl font-bold text-white">{userData.name.split(' ').map(n => n[0]).join('')}</span>
          </div>
          <h2 className="text-4xl font-bold text-gray-900 mb-4">Hello, {userData.name}! 🌟</h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Here's your personalized wellbeing journey. You've been amazing with {userData.totalResponses} responses and counting!
          </p>
        </div>

        {/* Main Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 text-center hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
            <div className="bg-gradient-to-r from-pink-400 to-red-500 p-4 rounded-2xl inline-flex mb-4">
              <Heart className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-3xl font-bold text-gray-900 mb-2">{userData.avgJoy}</h3>
            <p className="text-gray-600 font-medium">Average Joy</p>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
              <div 
                className="bg-gradient-to-r from-pink-400 to-red-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(userData.avgJoy / 10) * 100}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 text-center hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
            <div className="bg-gradient-to-r from-blue-400 to-blue-600 p-4 rounded-2xl inline-flex mb-4">
              <Target className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-3xl font-bold text-gray-900 mb-2">{userData.avgAchievement}</h3>
            <p className="text-gray-600 font-medium">Average Achievement</p>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
              <div 
                className="bg-gradient-to-r from-blue-400 to-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(userData.avgAchievement / 10) * 100}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 text-center hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
            <div className="bg-gradient-to-r from-purple-400 to-purple-600 p-4 rounded-2xl inline-flex mb-4">
              <Star className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-3xl font-bold text-gray-900 mb-2">{userData.avgMeaningfulness}</h3>
            <p className="text-gray-600 font-medium">Average Meaningfulness</p>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
              <div 
                className="bg-gradient-to-r from-purple-400 to-purple-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(userData.avgMeaningfulness / 10) * 100}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 text-center hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
            <div className="bg-gradient-to-r from-green-400 to-green-600 p-4 rounded-2xl inline-flex mb-4">
              <TrendingUp className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-3xl font-bold text-gray-900 mb-2">{userData.overallScore}</h3>
            <p className="text-gray-600 font-medium">Overall Wellbeing</p>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
              <div 
                className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(userData.overallScore / 10) * 100}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Insights Section */}
        <div className="mb-12">
          <h3 className="text-2xl font-bold text-gray-900 mb-8 text-center">Your Personal Insights</h3>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {insights.map((insight, index) => (
              <div key={index} className={`${insight.bgColor} rounded-3xl p-8 border-2 border-transparent hover:border-white transition-all duration-300 hover:shadow-lg`}>
                <div className={`bg-gradient-to-r ${insight.color} p-4 rounded-2xl inline-flex mb-6`}>
                  <insight.icon className="h-6 w-6 text-white" />
                </div>
                <h4 className={`text-xl font-bold mb-4 ${insight.textColor}`}>{insight.title}</h4>
                <p className={`${insight.textColor} leading-relaxed`}>{insight.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Responses */}
        <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-2xl font-bold text-gray-900">Recent Responses</h3>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <MessageSquare className="h-4 w-4" />
              <span>{userData.totalResponses} total responses</span>
            </div>
          </div>
          
          <div className="space-y-6">
            {responses.map((response, index) => (
              <div key={index} className="bg-gray-50 rounded-2xl p-6 hover:bg-gray-100 transition-colors">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <span className="font-medium text-gray-900">
                      {new Date(response.date).toLocaleDateString('en-US', { 
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full ${getScoreBg(response.joy)} mb-2`}>
                      <span className={`text-lg font-bold ${getScoreColor(response.joy)}`}>{response.joy}</span>
                    </div>
                    <p className="text-sm text-gray-600">Joy</p>
                  </div>
                  <div className="text-center">
                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full ${getScoreBg(response.achievement)} mb-2`}>
                      <span className={`text-lg font-bold ${getScoreColor(response.achievement)}`}>{response.achievement}</span>
                    </div>
                    <p className="text-sm text-gray-600">Achievement</p>
                  </div>
                  <div className="text-center">
                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full ${getScoreBg(response.meaningfulness)} mb-2`}>
                      <span className={`text-lg font-bold ${getScoreColor(response.meaningfulness)}`}>{response.meaningfulness}</span>
                    </div>
                    <p className="text-sm text-gray-600">Meaningfulness</p>
                  </div>
                </div>
                
                <div className="bg-white rounded-xl p-4">
                  <p className="text-gray-700 italic">"{response.influence}"</p>
                </div>
              </div>
            ))}
          </div>
          
          <div className="text-center mt-8">
            <button className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-8 py-3 rounded-full font-semibold hover:from-purple-600 hover:to-pink-600 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
              View All Responses
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PersonalAnalytics;