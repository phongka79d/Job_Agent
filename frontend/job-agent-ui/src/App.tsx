import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppShell from './components/AppShell';
import ReviewPage from './pages/ReviewPage';
import DashboardPage from './pages/DashboardPage';
import RoleProfilePanel from './components/RoleProfilePanel';
import IngestionPanel from './components/IngestionPanel';
import type { RoleProfile } from './types/api';
import { loadActiveBatchId, saveActiveBatchId } from './utils/activeBatchStorage';
import BatchMetrics from './components/BatchMetrics';
import './styles/app.css';

function App() {
  const [activeProfile, setActiveProfile] = useState<RoleProfile | null>(null);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [metricsRefreshCount, setMetricsRefreshCount] = useState(0);

  const handleProfileChange = (profile: RoleProfile) => {
    setActiveProfile(profile);
    
    // Reload the profile-specific active batch ID when switching role profiles.
    // If no stored key exists for this profile, storedBatchId will be null, resetting the state/metrics.
    const storedBatchId = loadActiveBatchId(profile.id);
    setActiveBatchId(storedBatchId);
  };

  const handleIngestionSuccess = (batchId: string) => {
    setActiveBatchId(batchId);
    if (activeProfile) {
      // Store response.batch_id as activeBatchId in component state and localStorage
      saveActiveBatchId(activeProfile.id, batchId);
    }
    triggerMetricsRefresh();
  };

  const triggerMetricsRefresh = () => {
    setMetricsRefreshCount((c) => c + 1);
  };


  const sidebar = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flexGrow: 1 }}>
      <RoleProfilePanel
        activeProfile={activeProfile}
        onProfileChange={handleProfileChange}
      />
      
      <IngestionPanel
        activeProfileId={activeProfile?.id || null}
        onIngestionSuccess={handleIngestionSuccess}
      />
      
      <BatchMetrics
        activeProfileId={activeProfile?.id || null}
        activeBatchId={activeBatchId}
        refreshTrigger={metricsRefreshCount}
      />
    </div>
  );

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell sidebarContent={sidebar} activeBatchId={activeBatchId} activeProfileId={activeProfile?.id || null} triggerMetricsRefresh={triggerMetricsRefresh} />}>
          <Route index element={<ReviewPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
