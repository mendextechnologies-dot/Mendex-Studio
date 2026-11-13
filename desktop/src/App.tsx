import React, { useState, useEffect } from 'react';
import { api } from './api/client';
import { OverviewData, ProjectRecord, SimulationJob } from './api/types';
import { Sidebar, RouteId } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { ProjectDetail } from './pages/ProjectDetail';
import { SimulationCenter } from './pages/SimulationCenter';
import { ComponentLibrary } from './pages/ComponentLibrary';
import { EngineeringTools } from './pages/EngineeringTools';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<RouteId>('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [overviewData, setOverviewData] = useState<OverviewData | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [simulations, setSimulations] = useState<SimulationJob[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<string>('');
  const [syncError, setSyncError] = useState('');
  const isSyncingRef = React.useRef(false);

  const syncData = async () => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;
    setIsSyncing(true);
    try {
      const [ov, projs, sims] = await Promise.all([
        api.overview(),
        api.projects(),
        api.simulations(),
      ]);
      setOverviewData(ov);
      setProjects(projs);
      setSimulations(sims);
      setLastSyncTime(new Date().toLocaleTimeString());
      setSyncError('');
    } catch (err) {
      console.error('Auto-sync error:', err);
      setSyncError(String(err));
    } finally {
      isSyncingRef.current = false;
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const pageParam = params.get('page') as RouteId;
    if (pageParam) {
      setCurrentRoute(pageParam);
    }
    const projParam = params.get('project');
    if (projParam) {
      setSelectedProjectId(projParam);
      setCurrentRoute('projects');
    }

    syncData();
    // 4.0s Real-time background synchronization
    const timer = setInterval(syncData, 4000);
    return () => clearInterval(timer);
  }, []);

  const handleSelectProject = (projectId: string) => {
    setSelectedProjectId(projectId);
    setCurrentRoute('projects');
  };

  const getPageTitle = () => {
    switch (currentRoute) {
      case 'dashboard':
        return 'Engineering Operations Dashboard';
      case 'projects':
        return selectedProjectId ? 'Project Deep-Dive & Lifecycle' : 'Engineering Projects Catalog';
      case 'simulations':
        return 'Simulation Center';
      case 'components':
        return 'Component & Materials Library';
      case 'tools':
        return 'Engineering Tool Health & Qualification';
      case 'reports':
        return 'Reports & Evidence Register';
      case 'settings':
        return 'Settings & System Diagnostics';
      default:
        return 'Mendex Engineering Studio';
    }
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <Sidebar
        currentRoute={currentRoute}
        onNavigate={(route) => {
          setCurrentRoute(route);
          if (route !== 'projects') {
            setSelectedProjectId(null);
          }
        }}
      />

      {/* Main View Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <Header
          title={getPageTitle()}
          isSyncing={isSyncing}
          lastSyncTime={lastSyncTime}
          onRefresh={syncData}
        />

        <main style={{ flex: 1, overflowY: 'auto', backgroundColor: 'var(--bg-app)' }}>
          {syncError && <p role="alert">Synchronization failed: {syncError}. Displayed records may be stale.</p>}
          {currentRoute === 'dashboard' && (
            <Dashboard
              data={overviewData}
              onSelectProject={handleSelectProject}
              onNavigateToSimulations={() => setCurrentRoute('simulations')}
            />
          )}

          {currentRoute === 'projects' && (
            selectedProjectId ? (
              <ProjectDetail
                projectId={selectedProjectId}
                onBack={() => setSelectedProjectId(null)}
              />
            ) : (
              <Projects
                projects={projects}
                onSelectProject={handleSelectProject}
              />
            )
          )}

          {currentRoute === 'simulations' && (
            <SimulationCenter jobs={simulations} />
          )}

          {currentRoute === 'components' && (
            <ComponentLibrary />
          )}

          {currentRoute === 'tools' && (
            <EngineeringTools />
          )}

          {currentRoute === 'reports' && (
            <Reports />
          )}

          {currentRoute === 'settings' && (
            <Settings />
          )}
        </main>
      </div>
    </div>
  );
};
