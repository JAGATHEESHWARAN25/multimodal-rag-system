import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import Login from '../Login';
import { AuthContext } from '../../context/AuthContext';

describe('Login Component', () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ is_first_time: false })
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderWithContext = () => {
    return render(
      <AuthContext.Provider value={{ login: mockLogin }}>
        <Login />
      </AuthContext.Provider>
    );
  };

  it('renders login form correctly', async () => {
    renderWithContext();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'RAG System' })).toBeInTheDOM();
    });
    expect(screen.getByLabelText('Username')).toBeInTheDOM();
    expect(screen.getByLabelText('Password')).toBeInTheDOM();
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDOM();
  });

  it('handles user input', async () => {
    renderWithContext();
    await waitFor(() => expect(screen.getByLabelText('Username')).toBeInTheDOM());
    const user = userEvent.setup();
    
    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'password123');

    expect(screen.getByLabelText('Username')).toHaveValue('admin');
    expect(screen.getByLabelText('Password')).toHaveValue('password123');
  });

  it('calls login function on submit', async () => {
    mockLogin.mockResolvedValueOnce({ success: true });
    renderWithContext();
    await waitFor(() => expect(screen.getByLabelText('Username')).toBeInTheDOM());
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(mockLogin).toHaveBeenCalledWith('admin', 'password123');
  });

  it('displays loading state during submission', async () => {
    let resolveLogin;
    mockLogin.mockReturnValueOnce(new Promise(resolve => {
      resolveLogin = resolve;
    }));

    renderWithContext();
    await waitFor(() => expect(screen.getByLabelText('Username')).toBeInTheDOM());
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(screen.getByRole('button', { name: /Signing in/i })).toBeDisabled();

    resolveLogin({ success: true });
  });

  it('displays error message on failed login', async () => {
    mockLogin.mockResolvedValueOnce({ success: false, error: 'Invalid credentials' });
    renderWithContext();
    await waitFor(() => expect(screen.getByLabelText('Username')).toBeInTheDOM());
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    await waitFor(() => {
      expect(screen.getByText('Unable to sign in. Please check your username and password and try again.')).toBeInTheDOM();
    });
  });

  it('displays default error message if none provided by backend', async () => {
    mockLogin.mockResolvedValueOnce({ success: false });
    renderWithContext();
    await waitFor(() => expect(screen.getByLabelText('Username')).toBeInTheDOM());
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    await waitFor(() => {
      expect(screen.getByText('Unable to sign in. Please check your username and password and try again.')).toBeInTheDOM();
    });
  });
});
