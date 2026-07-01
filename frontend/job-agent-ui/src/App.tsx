import { useState, useEffect } from 'react';
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
import ConversationToolbar from './components/chat/ConversationToolbar';
import { listConversations, deleteConversation } from './api/chatClient';
import type { ChatConversation } from './types/chat';
import './styles/app.css';

function App() {
  const [activeProfile, setActiveProfile] = useState<RoleProfile | null>(null);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [metricsRefreshCount, setMetricsRefreshCount] = useState(0);

  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [conversationError, setConversationError] = useState<string | null>(null);

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

  useEffect(() => {
    if (!activeProfile) {
      setConversations([]);
      setActiveConversationId(null);
      setConversationError(null);
      return;
    }

    const loadHistory = async () => {
      try {
        setConversationError(null);
        const history = await listConversations(activeProfile.id);
        setConversations(history);
        setActiveConversationId(null);
      } catch (err) {
        setConversationError(err instanceof Error ? err.message : 'Failed to load chat history.');
      }
    };

    void loadHistory();
  }, [activeProfile]);

  const handleSelectConversation = (selected: ChatConversation) => {
    setActiveConversationId(selected.id);
  };

  const handleNewConversation = () => {
    setActiveConversationId(null);
  };

  const handleDeleteConversation = async (target: ChatConversation) => {
    if (!activeProfile) return;
    try {
      setConversationError(null);
      await deleteConversation(target.id);
      if (activeConversationId === target.id) {
        setActiveConversationId(null);
      }
      const history = await listConversations(activeProfile.id);
      setConversations(history);
    } catch (err) {
      setConversationError(err instanceof Error ? err.message : 'Failed to delete conversation.');
    }
  };

  const handleConversationCreated = async (created: ChatConversation) => {
    if (!activeProfile) return;
    try {
      setConversationError(null);
      const history = await listConversations(activeProfile.id);
      setConversations(history);
      setActiveConversationId(created.id);
    } catch (err) {
      setConversationError(
        err instanceof Error ? err.message : 'Failed to refresh chat history.',
      );
      setConversations((prev) => [created, ...prev]);
      setActiveConversationId(created.id);
    }
  };

  const handleMessageSent = async () => {
    if (!activeProfile) return;
    try {
      setConversationError(null);
      const history = await listConversations(activeProfile.id);
      setConversations(history);
    } catch (err) {
      setConversationError(
        err instanceof Error ? err.message : 'Failed to refresh chat history.',
      );
    }
  };

  const sidebar = (
    <div className="workspace-sidebar-content">
      <RoleProfilePanel
        activeProfile={activeProfile}
        onProfileChange={handleProfileChange}
      />
      <div className="rail-section">
        <div className="rail-section-heading">
          <span>Chat history</span>
        </div>
        {conversationError ? <div className="error-text">{conversationError}</div> : null}
        <ConversationToolbar
          conversations={conversations}
          activeConversationId={activeConversationId}
          disabled={!activeProfile || isSending}
          onSelect={handleSelectConversation}
          onCreate={handleNewConversation}
          onDelete={(target) => void handleDeleteConversation(target)}
        />
      </div>
    </div>
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
          <Route
            index
            element={(
              <ChatWorkspacePage
                contextOverride={{
                  activeConversationId,
                  onConversationCreated: handleConversationCreated,
                  onMessageSent: handleMessageSent,
                  isSendingGlobal: isSending,
                  setIsSendingGlobal: setIsSending,
                }}
              />
            )}
          />
          <Route path="review" element={<ReviewPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
