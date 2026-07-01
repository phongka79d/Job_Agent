import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppShell from './components/AppShell';
import ReviewPage from './pages/ReviewPage';
import DashboardPage from './pages/DashboardPage';
import ChatWorkspacePage from './pages/ChatWorkspacePage';
import RoleProfilePanel from './components/RoleProfilePanel';
import IngestionPanel from './components/IngestionPanel';
import ProfileDocumentPanel from './components/profile/ProfileDocumentPanel';
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
    
    const storedBatchId = loadActiveBatchId(profile.id);
    setActiveBatchId(storedBatchId);
  };

  const handleIngestionSuccess = (batchId: string) => {
    setActiveBatchId(batchId);
    if (activeProfile) {
      saveActiveBatchId(activeProfile.id, batchId);
    }
    triggerMetricsRefresh();
  };

  const triggerMetricsRefresh = () => {
    setMetricsRefreshCount((c) => c + 1);
  };


  const sidebar = (
    <RoleProfilePanel
      activeProfile={activeProfile}
      onProfileChange={handleProfileChange}
    />
  );

  const context = (
    <div className="workspace-context-content">
      <ProfileDocumentPanel activeProfileId={activeProfile?.id || null} />

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
        <Route
          path="/"
          element={(
            <AppShell
              sidebarContent={sidebar}
              contextContent={context}
              activeBatchId={activeBatchId}
              activeProfileId={activeProfile?.id || null}
              triggerMetricsRefresh={triggerMetricsRefresh}
            />
          )}
        >
          <Route index element={<ChatWorkspacePage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
