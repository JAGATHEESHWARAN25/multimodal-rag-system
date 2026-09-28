import React, { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(sessionStorage.getItem('token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      sessionStorage.setItem('token', token);
      localStorage.setItem('token', token);
      fetchUser(token);
    } else {
      sessionStorage.removeItem('token');
      localStorage.removeItem('token');
      setUser(null);
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async (authToken) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    try {
      const res = await fetch('http://localhost:8000/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        // Token invalid or expired
        setToken(null);
      }
    } catch (err) {
      console.error("Failed to fetch user:", err);
      // Don't auto-logout on network error to allow retry
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    try {
      const res = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      const data = await res.json();
      if (res.ok) {
        setToken(data.access_token);
        return { success: true };
      } else {
        return { success: false, error: data.detail };
      }
    } catch (err) {
      clearTimeout(timeoutId);
      return { success: false, error: "Backend is currently restarting or loading AI models. Please wait 1-2 minutes and try again." };
    }
  };

  const logout = () => {
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, setToken, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
