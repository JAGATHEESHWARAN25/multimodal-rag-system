import React, { useState, useEffect } from 'react';
import { BACKEND_URL } from '../App';

export default function AuditLogs({ token }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/system/audit`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleExport = async (format) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/system/audit/export?format=${format}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_logs.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (err) {
      console.error("Failed to export audit logs:", err);
    }
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h3 style={{ fontWeight: "600", margin: 0 }}>System Audit Logs</h3>
        <div style={{ display: "flex", gap: "8px" }}>
          <button className="btn btn-secondary" onClick={() => handleExport('csv')} style={{ padding: "6px 12px", fontSize: "12px" }}>
            📥 Export CSV
          </button>
          <button className="btn btn-secondary" onClick={() => handleExport('json')} style={{ padding: "6px 12px", fontSize: "12px" }}>
            📥 Export JSON
          </button>
          <button className="btn btn-secondary" onClick={fetchLogs} style={{ padding: "6px 12px", fontSize: "12px" }}>
            Refresh
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", background: "var(--bg-sidebar)" }}>
        {loading ? (
          <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>Loading logs...</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>No audit logs found.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
            <thead style={{ background: "rgba(0,0,0,0.2)", position: "sticky", top: 0, zIndex: 1 }}>
              <tr>
                <th style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-glass)", fontWeight: "600", color: "var(--text-muted)" }}>Timestamp</th>
                <th style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-glass)", fontWeight: "600", color: "var(--text-muted)" }}>User</th>
                <th style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-glass)", fontWeight: "600", color: "var(--text-muted)" }}>Event</th>
                <th style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-glass)", fontWeight: "600", color: "var(--text-muted)" }}>Action</th>
                <th style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-glass)", fontWeight: "600", color: "var(--text-muted)" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid var(--border-glass)" }}>
                  <td style={{ padding: "12px 16px", color: "var(--text-main)" }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td style={{ padding: "12px 16px", color: "var(--color-accent)" }}>
                    {log.username}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ 
                      padding: "2px 8px", 
                      borderRadius: "4px", 
                      background: "rgba(99, 102, 241, 0.1)",
                      color: "var(--color-accent)",
                      fontSize: "11px",
                      fontWeight: "500"
                    }}>
                      {log.event_type}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px", color: "var(--text-main)" }}>
                    {log.action}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ 
                      padding: "2px 8px", 
                      borderRadius: "4px", 
                      background: log.status === 'SUCCESS' ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                      color: log.status === 'SUCCESS' ? "#10b981" : "#ef4444",
                      fontSize: "11px",
                      fontWeight: "500"
                    }}>
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
