import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', padding: 60, textAlign: 'center',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
          <h2 style={{ marginBottom: 8 }}>Xatolik yuz berdi</h2>
          <p style={{ color: 'var(--text-muted)', maxWidth: 400, marginBottom: 24 }}>
            {this.state.error.message}
          </p>
          <button onClick={() => { this.setState({ error: null }); window.location.reload() }}
            style={{
              padding: '12px 32px', borderRadius: 'var(--radius)', border: 'none',
              background: 'var(--primary)', color: '#fff', fontSize: 15, cursor: 'pointer',
            }}>
            Qayta yuklash
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
