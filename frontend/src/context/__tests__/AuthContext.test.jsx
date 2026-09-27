import React, { useContext } from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AuthProvider, AuthContext } from '../AuthContext';

const TestComponent = () => {
  const { user, token, login, logout, loading } = useContext(AuthContext);
  return (
    <div>
      <div data-testid="loading">{loading ? 'loading' : 'ready'}</div>
      <div data-testid="token">{token || 'no-token'}</div>
      <div data-testid="user">{user ? user.username : 'no-user'}</div>
      <button onClick={() => login('admin', 'password123')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });



  it('provides initial unauthenticated state when no token exists', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    expect(screen.getByTestId('loading')).toHaveTextContent('ready');
    expect(screen.getByTestId('token')).toHaveTextContent('no-token');
    expect(screen.getByTestId('user')).toHaveTextContent('no-user');
  });

  it('restores token from sessionStorage and fetches user', async () => {
    sessionStorage.setItem('token', 'fake-jwt-token');
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ username: 'admin', role: 'SYSTEM_ADMIN' })
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Should start loading, then resolve
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('ready');
    });

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/me', expect.objectContaining({
      headers: { 'Authorization': 'Bearer fake-jwt-token' }
    }));
    
    expect(screen.getByTestId('token')).toHaveTextContent('fake-jwt-token');
    expect(screen.getByTestId('user')).toHaveTextContent('admin');
  });

  it('clears token if fetch user fails with invalid token', async () => {
    sessionStorage.setItem('token', 'invalid-jwt');
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Invalid token' })
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('ready');
    });

    expect(screen.getByTestId('token')).toHaveTextContent('no-token');
    expect(sessionStorage.getItem('token')).toBeNull();
  });

  it('handles successful login', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'new-token' })
    }).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ username: 'admin', role: 'SYSTEM_ADMIN' })
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await userEvent.click(screen.getByText('Login'));

    await waitFor(() => {
      expect(screen.getByTestId('token')).toHaveTextContent('new-token');
      expect(sessionStorage.getItem('token')).toBe('new-token');
    });
  });

  it('handles failed login', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Incorrect credentials' })
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await userEvent.click(screen.getByText('Login'));

    await waitFor(() => {
      expect(screen.getByTestId('token')).toHaveTextContent('no-token');
    });
  });

  it('handles logout', async () => {
    sessionStorage.setItem('token', 'fake-token');
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ username: 'admin' })
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('fake-token'));

    await userEvent.click(screen.getByText('Logout'));

    await waitFor(() => {
      expect(screen.getByTestId('token')).toHaveTextContent('no-token');
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
      expect(sessionStorage.getItem('token')).toBeNull();
    });
  });
});
