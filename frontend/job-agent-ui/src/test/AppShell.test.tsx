import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useOutletContext } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import AppShell from '../components/AppShell';

interface ShellOutletContext {
  activeProfileId: string | null;
  activeBatchId: string | null;
  triggerMetricsRefresh: () => void;
}

function RouteContent() {
  const { activeProfileId, activeBatchId } = useOutletContext<ShellOutletContext>();

  return (
    <div>
      Route content for {activeProfileId} and {activeBatchId}
    </div>
  );
}

function renderShell(activeBatchId: string | null) {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route
          path="/"
          element={(
            <AppShell
              sidebarContent={<div>Sidebar content</div>}
              contextContent={<div>Context content</div>}
              activeBatchId={activeBatchId}
              activeProfileId="profile-from-api"
              triggerMetricsRefresh={vi.fn()}
            />
          )}
        >
          <Route index element={<RouteContent />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('AppShell', () => {
  it('renders the three workspace regions, routes, links, and real shell values', () => {
    const { container } = renderShell('batch-from-api');

    expect(container.querySelector('aside.workspace-sidebar')).toHaveTextContent('Sidebar content');
    expect(container.querySelector('main.workspace-main')).toHaveTextContent(
      'Route content for profile-from-api and batch-from-api',
    );
    expect(container.querySelector('aside.workspace-context')).toHaveTextContent('Context content');

    expect(screen.getByRole('link', { name: 'Agent Chat' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Review Queue' })).toHaveAttribute('href', '/review');
    expect(screen.getByRole('link', { name: 'Tracked Jobs' })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByText('batch-from-api')).toBeInTheDocument();
  });

  it('omits the active batch badge and None fallback without an active batch', () => {
    renderShell(null);

    expect(screen.queryByText(/Active batch/i)).not.toBeInTheDocument();
    expect(screen.queryByText('None')).not.toBeInTheDocument();
  });
});
