import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import CoaTest from './CoaTest.jsx'
import ControlTowerApp from './control-tower/ControlTowerApp.jsx'

// Views: 'app' | 'coa' | 'tower'
function MainRouter() {
  const [view, setView] = useState('app');

  const navBtn = (target, label, color) => (
    <button
      onClick={() => setView(target)}
      style={{
        padding: '8px 16px',
        background: view === target ? color : 'transparent',
        color: view === target ? 'black' : color,
        border: `2px solid ${color}`,
        cursor: 'pointer',
        fontWeight: 'bold',
        fontFamily: 'monospace',
        fontSize: '11px',
        letterSpacing: '1px',
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Navigation bar — only visible outside Control Tower */}
      {view !== 'tower' && (
        <div style={{
          background: '#0f0f1b',
          padding: '8px 16px',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          gap: '8px',
          borderBottom: '1px solid #333'
        }}>
          {navBtn('app', '📊 FIN-SYS APP', '#4facfe')}
          {navBtn('coa', '🧪 TEST COA', '#ff4b2b')}
          {navBtn('tower', '⬡ CONTROL TOWER', '#fbbf24')}
        </div>
      )}
      <div style={{ flex: 1, overflow: view === 'tower' ? 'hidden' : 'auto' }}>
        {view === 'app' && <App />}
        {view === 'coa' && <CoaTest />}
        {view === 'tower' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Back button overlay for Control Tower */}
            <ControlTowerApp onGoBack={() => setView('app')} />
          </div>
        )}
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MainRouter />
  </StrictMode>,
)
