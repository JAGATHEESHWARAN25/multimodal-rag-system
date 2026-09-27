import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isFirstTime, setIsFirstTime] = useState(false);
  const [checkingSetup, setCheckingSetup] = useState(true);
  
  const { login, setToken } = useContext(AuthContext);

  useEffect(() => {
    const checkSetupStatus = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/auth/setup-status');
        if (res.ok) {
          const data = await res.json();
          setIsFirstTime(data.is_first_time);
        }
      } catch (err) {
        console.error("Failed to fetch setup status:", err);
      } finally {
        setCheckingSetup(false);
      }
    };
    checkSetupStatus();
  }, []);

  const handleInitialSetupSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify your password entry.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/auth/initial-setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password: password.trim() })
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.access_token);
      } else {
        setError(data.detail || 'Failed to complete initial setup.');
      }
    } catch (err) {
      setError('Network error completing initial setup.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    
    setError('');
    setLoading(true);
    
    const result = await login(username.trim(), password.trim());
    if (!result.success) {
      setError('Unable to sign in. Please check your username and password and try again.');
    }
    setLoading(false);
  };

  if (checkingSetup) {
    return (
      <div className="login-wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading workspace initialization status...</div>
      </div>
    );
  }

  return (
    <div className="login-wrapper">
      <div className="login-card">
        {/* Header / Brand */}
        <div className="login-header">
          <div className="login-logo-mark" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <line x1="10" y1="9" x2="8" y2="9"></line>
            </svg>
          </div>
          <h1 className="login-title">RAG System</h1>
          <p className="login-subtitle">
            {isFirstTime ? 'First-Time Workspace Setup' : 'Retrieval-Augmented Generation Workspace'}
          </p>
        </div>

        {/* Polished Inline Error Alert */}
        {error && (
          <div className="login-error-alert" role="alert">
            <div className="login-error-icon" aria-hidden="true">⚠️</div>
            <div className="login-error-text">
              <strong>{isFirstTime ? 'Setup Error' : 'Unable to sign in'}</strong>
              <span>{error}</span>
            </div>
            <button 
              type="button" 
              className="login-error-dismiss" 
              onClick={() => setError('')}
              aria-label="Dismiss error notification"
            >
              ×
            </button>
          </div>
        )}

        {isFirstTime ? (
          /* First Time Setup Wizard Form */
          <form onSubmit={handleInitialSetupSubmit} className="login-form">
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '14px', textAlign: 'center' }}>
              Create your primary administrator account to initialize this installation.
            </div>
            <div className="form-group">
              <label htmlFor="username" className="form-label">
                Master Username
              </label>
              <input 
                id="username"
                type="text" 
                className="form-input"
                value={username} 
                onChange={(e) => { setUsername(e.target.value); if (error) setError(''); }} 
                placeholder="Choose username"
                required 
                disabled={loading}
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="password" className="form-label">
                Master Password
              </label>
              <input 
                id="password"
                type="password" 
                className="form-input"
                value={password} 
                onChange={(e) => { setPassword(e.target.value); if (error) setError(''); }} 
                placeholder="Set password (min. 6 characters)"
                required 
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword" className="form-label">
                Confirm Password
              </label>
              <input 
                id="confirmPassword"
                type="password" 
                className="form-input"
                value={confirmPassword} 
                onChange={(e) => { setConfirmPassword(e.target.value); if (error) setError(''); }} 
                placeholder="Confirm password"
                required 
                disabled={loading}
              />
            </div>

            <button 
              type="submit" 
              className="login-submit-btn"
              disabled={loading || !username.trim() || !password.trim() || !confirmPassword.trim()}
            >
              {loading ? 'Initializing Workspace...' : 'Create Account & Initialize'}
            </button>
          </form>
        ) : (
          /* Credentials Form */
          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="username" className="form-label">
                Username
              </label>
              <input 
                id="username"
                type="text" 
                className="form-input"
                value={username} 
                onChange={(e) => { setUsername(e.target.value); if (error) setError(''); }} 
                placeholder="Enter your username"
                required 
                disabled={loading}
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <div className="password-input-wrapper">
                <input 
                  id="password"
                  type={showPassword ? 'text' : 'password'} 
                  className="form-input password-input"
                  value={password} 
                  onChange={(e) => { setPassword(e.target.value); if (error) setError(''); }} 
                  placeholder="Enter your password"
                  required 
                  disabled={loading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  tabIndex={0}
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button 
              type="submit" 
              className="login-submit-btn"
              disabled={loading || !username.trim() || !password.trim()}
            >
              {loading ? (
                <span className="login-loading-state">
                  <span className="login-spinner" aria-hidden="true"></span>
                  <span>Signing in…</span>
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        )}

        {/* Security & System Footer */}
        <div className="login-footer">
          <span className="login-secure-tag">
            <span className="login-status-dot" aria-hidden="true"></span>
            Local / Secure Access
          </span>
        </div>
      </div>
    </div>
  );
}
