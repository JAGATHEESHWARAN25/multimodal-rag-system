
import React, { useState, useEffect } from 'react';

const BACKEND_URL = 'http://localhost:8000';

export default function UserManagement({ token }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '', role: 'USER' });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(BACKEND_URL + '/api/auth/users', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to fetch users');
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(BACKEND_URL + '/api/auth/users', {
        method: 'POST',
        headers: { 
          'Authorization': 'Bearer ' + token,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ ...formData, role: 'USER' })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to create user');
      setShowCreateForm(false);
      setFormData({ username: '', password: '', role: 'USER' });
      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    try {
      const res = await fetch(BACKEND_URL + '/api/auth/users/' + userId, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to delete user');
      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div>Loading users...</div>;

  return (
    <div className='panel' style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>User Management</h2>
        <button className='btn btn-primary' onClick={() => setShowCreateForm(!showCreateForm)}>
          {showCreateForm ? 'Cancel' : 'Create New User Account'}
        </button>
      </div>
      
      {error && <div style={{ color: 'var(--color-danger)', marginBottom: '10px' }}>{error}</div>}

      {showCreateForm && (
        <form onSubmit={handleCreate} style={{ marginBottom: '20px', padding: '15px', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
          <h3 style={{ fontSize: '15px', marginBottom: '12px' }}>Create User Profile</h3>
          <div style={{ display: 'flex', gap: '10px' }}>
            <input type='text' placeholder='Username' value={formData.username} onChange={e => setFormData({...formData, username: e.target.value})} required className='input-box' style={{ flex: 1 }} />
            <input type='password' placeholder='Password' value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} required className='input-box' style={{ flex: 1 }} />
            <button type='submit' className='btn btn-primary'>Save User</button>
          </div>
        </form>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', background: 'var(--bg-sidebar)', borderRadius: '8px', overflow: 'hidden' }}>
        <thead>
          <tr style={{ background: 'rgba(0,0,0,0.2)', textAlign: 'left' }}>
            <th style={{ padding: '12px' }}>Username</th>
            <th style={{ padding: '12px' }}>Created At</th>
            <th style={{ padding: '12px' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
              <td style={{ padding: '12px', fontWeight: '600' }}>{u.username}</td>
              <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{new Date(u.created_at).toLocaleString()}</td>
              <td style={{ padding: '12px' }}>
                <button className='btn btn-secondary' onClick={() => handleDelete(u.id)}>Delete Account</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
