/* ============================================================
   ErrorBoundary.jsx — Captura errores de render por módulo.
   Si un módulo crashea, solo ESE módulo muestra el fallback.
   El Shell, Sidebar y otros módulos siguen funcionando.
   
   Analogía: SAP Fiori Launchpad — si una app falla, el
   launchpad no se cae. Netflix — si "Mi Lista" falla,
   el player sigue intacto.
   ============================================================ */
import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // Log para debugging — en producción se enviaría a un servicio de monitoreo
    console.error(
      `[ErrorBoundary] Módulo "${this.props.module}" crasheó:`,
      error,
      errorInfo
    );
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 300,
          fontFamily: 'var(--shell-font, "IBM Plex Mono", monospace)',
          padding: 32,
          textAlign: 'center',
        }}>
          {/* Icono de error */}
          <div style={{
            fontSize: 48,
            marginBottom: 16,
            filter: 'grayscale(0.3)',
          }}>
            ⚠️
          </div>

          {/* Título */}
          <h2 style={{
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: 2,
            textTransform: 'uppercase',
            color: '#1a1a1a',
            margin: '0 0 8px 0',
            borderBottom: '2px solid #000',
            paddingBottom: 8,
          }}>
            Error en módulo: {this.props.module || 'Desconocido'}
          </h2>

          {/* Mensaje */}
          <p style={{
            fontSize: 11,
            color: '#666',
            maxWidth: 400,
            lineHeight: 1.6,
            margin: '8px 0 16px',
          }}>
            Este módulo encontró un error inesperado. El resto del sistema
            sigue funcionando. Puedes intentar recargar el módulo o navegar
            a otro desde la barra lateral.
          </p>

          {/* Detalle técnico (colapsable) */}
          <details style={{
            fontSize: 10,
            color: '#999',
            maxWidth: 500,
            width: '100%',
            textAlign: 'left',
            marginBottom: 16,
            border: '1px solid #ddd',
            padding: 8,
            background: '#fafafa',
          }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, color: '#666' }}>
              Detalle técnico
            </summary>
            <pre style={{
              marginTop: 8,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: 9,
              color: '#c00',
            }}>
              {this.state.error?.toString()}
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>

          {/* Botón de retry */}
          <button
            onClick={this.handleRetry}
            style={{
              padding: '8px 24px',
              fontSize: 11,
              fontWeight: 700,
              fontFamily: 'inherit',
              letterSpacing: 2,
              textTransform: 'uppercase',
              background: '#000',
              color: '#fff',
              border: '2px solid #000',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => {
              e.target.style.background = '#fff';
              e.target.style.color = '#000';
            }}
            onMouseLeave={e => {
              e.target.style.background = '#000';
              e.target.style.color = '#fff';
            }}
          >
            ↻ Reintentar módulo
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
