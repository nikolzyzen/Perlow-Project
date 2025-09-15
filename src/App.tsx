import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminDashboard from './components/AdminDashboard';
import PersonalAnalytics from './components/PersonalAnalytics';
import UserManagement from './components/UserManagement';
import CampaignManagement from './components/CampaignManagement';
import ResponsesView from './components/ResponsesView';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<AdminDashboard />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="/campaigns" element={<CampaignManagement />} />
          <Route path="/responses" element={<ResponsesView />} />
          <Route path="/analytics/:userId/:campaignId" element={<PersonalAnalytics />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;