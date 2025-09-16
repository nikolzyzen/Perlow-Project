import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Users, Plus, Search, Phone, Calendar, MoreVertical } from 'lucide-react';

interface User {
  id: number;
  name: string;
  phone: string;
  status: string;
  joinDate: string;
  responses: number;
  lastResponse: string;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/users');
        if (response.ok) {
          const data = await response.json();
          setUsers(data);
        } else {
          // Fallback to sample data if API fails
          setUsers([
    {
      id: 1,
      name: 'Sarah Johnson',
      phone: '+1 (555) 123-4567',
      status: 'Active',
      joinDate: '2024-01-15',
      responses: 28,
      lastResponse: '2 hours ago'
    },
    {
      id: 2,
      name: 'Mike Chen',
      phone: '+1 (555) 234-5678',
      status: 'Active',
      joinDate: '2024-01-10',
      responses: 22,
      lastResponse: '1 day ago'
    },
    {
      id: 3,
      name: 'Emily Rodriguez',
      phone: '+1 (555) 345-6789',
      status: 'Inactive',
      joinDate: '2023-12-20',
      responses: 15,
      lastResponse: '1 week ago'
    },
    {
      id: 4,
      name: 'David Kim',
      phone: '+1 (555) 456-7890',
      status: 'Active',
      joinDate: '2024-01-08',
      responses: 31,
      lastResponse: '30 minutes ago'
          ]);
        }
      } catch (error) {
        console.error('Error fetching users:', error);
        // Keep fallback data on error
        setUsers([
          {
            id: 1,
            name: 'Sarah Johnson',
            phone: '+1 (555) 123-4567',
            status: 'Active',
            joinDate: '2024-01-15',
            responses: 28,
            lastResponse: '2 hours ago'
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
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
              <div className="bg-gradient-to-r from-blue-500 to-purple-500 p-2 rounded-xl">
                <Users className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">User Management</h1>
                <p className="text-sm text-gray-500">Manage survey participants</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions Bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0 mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">All Users</h2>
            <p className="text-gray-600">{users.length} total participants</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search users..."
                className="pl-10 pr-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <button className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-2 rounded-xl font-semibold hover:from-blue-600 hover:to-purple-600 transition-all duration-300 flex items-center space-x-2">
              <Plus className="h-4 w-4" />
              <span>Add User</span>
            </button>
          </div>
        </div>

        {/* Users Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {users.map((user) => (
            <div key={user.id} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-300 hover:-translate-y-1">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full flex items-center justify-center">
                    <span className="text-white font-semibold text-lg">
                      {user.name.split(' ').map(n => n[0]).join('')}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{user.name}</h3>
                    <div className="flex items-center space-x-1 text-sm text-gray-500">
                      <Phone className="h-3 w-3" />
                      <span>{user.phone}</span>
                    </div>
                  </div>
                </div>
                <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors">
                  <MoreVertical className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Status</span>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    user.status === 'Active' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {user.status}
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Responses</span>
                  <span className="font-semibold text-gray-900">{user.responses}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Last Response</span>
                  <span className="text-sm text-gray-600">{user.lastResponse}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Joined</span>
                  <div className="flex items-center space-x-1 text-sm text-gray-600">
                    <Calendar className="h-3 w-3" />
                    <span>{new Date(user.joinDate).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-100">
                <button className="w-full bg-gradient-to-r from-blue-50 to-purple-50 text-blue-600 hover:text-blue-800 py-2 px-4 rounded-xl font-medium transition-colors">
                  View Analytics
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UserManagement;