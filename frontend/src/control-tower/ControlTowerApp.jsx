// ControlTowerApp.jsx — Componente raíz del módulo Control Tower
import React, { useState } from 'react';
import { useControlTower } from './hooks/useControlTower';
import CTLoginRegister from './components/CTLoginRegister';
import CTTopBar from './components/CTTopBar';
import CTKpiCards from './components/CTKpiCards';
import CTEntityTree from './components/CTEntityTree';
import CTSidePanel from './components/CTSidePanel';
import CTApprovalsCenter from './components/CTApprovalsCenter';
import CTResourceIds from './components/CTResourceIds';
import CTCollaborators from './components/CTCollaborators';

export default function ControlTowerApp({ onGoBack }) {
  const ct = useControlTower();

  const [showApprovals, setShowApprovals] = useState(false);
  const [showResources, setShowResources] = useState(false);
  const [showCollaborators, setShowCollaborators] = useState(false);

  const handleSelectEntity = (entity, parentChain) => {
    ct.selectEntity(entity, parentChain);
  };

  const handleBreadcrumbNavigate = (entity) => {
    // Find parent chain up to this entity from the full tree
    ct.selectEntity(entity, ct.breadcrumb.slice(0, ct.breadcrumb.findIndex(e => e.id === entity.id)));
  };

  const handleGoHome = () => {
    ct.selectEntity(null, []);
  };

  // ── Not logged in ──────────────────────────────────────────
  if (!ct.session) {
    return (
      <CTLoginRegister
        onLogin={ct.login}
        onRegister={ct.register}
        isLoading={ct.isLoading}
      />
    );
  }

  // ── Main Dashboard ─────────────────────────────────────────
  return (
    <div className="h-screen flex flex-col bg-black font-mono overflow-hidden">
      {/* Top Bar */}
      <CTTopBar
        session={ct.session}
        onLogout={ct.logout}
        onGoBack={onGoBack}
        activeEntity={ct.activeEntity}
        entities={ct.entities}
        onSelectEntity={(entity) => ct.selectEntity(entity, [])}
        breadcrumb={ct.breadcrumb}
        onNavigate={handleBreadcrumbNavigate}
        onGoHome={handleGoHome}
      />

      {/* Zone 1 — KPI Cards */}
      <div className="border-b-2 border-amber-400/30 flex-shrink-0 bg-black">
        <CTKpiCards
          kpis={ct.kpis}
          activeEntity={ct.activeEntity}
          onOpenApprovals={() => setShowApprovals(true)}
        />
      </div>

      {/* Main Body — Zones 2 & 3 */}
      <div className="flex flex-1 overflow-hidden">
        {/* Zone 2 — Entity Tree (main content) */}
        <div className="flex-1 overflow-hidden border-r-2 border-amber-400/30 bg-black">
          <CTEntityTree
            entities={ct.entities}
            activeEntity={ct.activeEntity}
            onSelect={handleSelectEntity}
            onDelete={ct.deleteEntity}
            onCreate={ct.createEntity}
          />
        </div>

        {/* Zone 3 — Side Panel */}
        <div className="w-64 flex-shrink-0 bg-black">
          <CTSidePanel
            activeEntity={ct.activeEntity}
            session={ct.session}
            onOpenApprovals={() => setShowApprovals(true)}
            onOpenResources={() => setShowResources(true)}
            onOpenCollaborators={() => setShowCollaborators(true)}
            onQuickTransaction={ct.quickTransaction}
          />
        </div>
      </div>

      {/* ── Modals ─────────────────────────────────────────── */}
      {showApprovals && (
        <CTApprovalsCenter
          approvals={ct.approvals}
          onResolve={ct.resolveApproval}
          onCreateApproval={ct.createApproval}
          activeEntity={ct.activeEntity}
          onClose={() => setShowApprovals(false)}
        />
      )}

      {showResources && (
        <CTResourceIds
          resources={ct.resources}
          onCreateResource={ct.createResource}
          onDeleteResource={ct.deleteResource}
          activeEntity={ct.activeEntity}
          onClose={() => setShowResources(false)}
        />
      )}

      {showCollaborators && (
        <CTCollaborators
          members={ct.members}
          users={ct.users}
          activeEntity={ct.activeEntity}
          onInvite={ct.inviteMember}
          onClose={() => setShowCollaborators(false)}
        />
      )}
    </div>
  );
}
