import React, { useState, useEffect } from "react";

export default function ChatSidebar({ 
    activeSessionId, 
    onSelectSession, 
    onNewSession,
    backendUrl,
    token,
    triggerRefresh
}) {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(false);

    const fetchSessions = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${backendUrl}/api/chat/sessions`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setSessions(data);
            }
        } catch (e) {
            console.error("Failed to load sessions", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token) fetchSessions();
    }, [token, triggerRefresh]);

    const handleDelete = async (e, sessionId) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this session?")) return;
        
        try {
            const res = await fetch(`${backendUrl}/api/chat/sessions/${sessionId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                if (activeSessionId === sessionId) {
                    onNewSession();
                } else {
                    fetchSessions();
                }
            }
        } catch (err) {
            console.error("Delete failed", err);
        }
    };

    return (
        <div style={{ 
            width: '260px', 
            minWidth: '260px',
            borderRight: '1px solid var(--border-glass)', 
            display: 'flex', 
            flexDirection: 'column', 
            backgroundColor: 'var(--bg-sidebar)',
            height: '100%'
        }}>
            <div style={{ padding: '16px', borderBottom: '1px solid var(--border-glass)' }}>
                <button 
                    onClick={onNewSession}
                    style={{
                        width: '100%',
                        padding: '10px 14px',
                        background: 'linear-gradient(135deg, var(--color-accent), var(--color-accent-purple))',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        fontWeight: '600',
                        fontSize: '13px',
                        boxShadow: '0 4px 12px rgba(99, 102, 241, 0.25)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        transition: 'all 0.2s ease'
                    }}
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    + New Chat
                </button>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
                <h4 style={{ padding: '4px 8px 10px 8px', fontSize: '11px', fontWeight: '700', letterSpacing: '0.5px', textTransform: 'uppercase', color: 'var(--text-muted)', margin: 0 }}>
                    Recent History
                </h4>
                {loading && sessions.length === 0 ? (
                    <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>Loading sessions...</div>
                ) : sessions.length === 0 ? (
                    <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>No previous sessions</div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {sessions.map(session => {
                            const isActive = activeSessionId === session.id;
                            return (
                                <div 
                                    key={session.id}
                                    onClick={() => onSelectSession(session.id)}
                                    style={{
                                        padding: '10px 12px',
                                        borderRadius: 'var(--radius-md)',
                                        cursor: 'pointer',
                                        backgroundColor: isActive ? 'rgba(99, 102, 241, 0.12)' : 'transparent',
                                        border: isActive ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        transition: 'all 0.2s ease'
                                    }}
                                    onMouseEnter={(e) => {
                                        if (!isActive) e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
                                    }}
                                    onMouseLeave={(e) => {
                                        if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                                    }}
                                >
                                    <div style={{ 
                                        overflow: 'hidden', 
                                        whiteSpace: 'nowrap', 
                                        textOverflow: 'ellipsis', 
                                        fontSize: '13px', 
                                        fontWeight: isActive ? '600' : '400',
                                        color: isActive ? 'var(--color-accent)' : 'var(--text-main)',
                                        flex: 1,
                                        marginRight: '8px'
                                    }}>
                                        💬 {session.title || "New Chat Session"}
                                    </div>
                                    <button 
                                        onClick={(e) => handleDelete(e, session.id)}
                                        style={{
                                            background: 'none', 
                                            border: 'none', 
                                            cursor: 'pointer', 
                                            color: 'var(--text-muted)', 
                                            padding: '4px',
                                            borderRadius: '4px',
                                            display: 'flex',
                                            alignItems: 'center'
                                        }}
                                        title="Delete Session"
                                        onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-danger)'}
                                        onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                    >
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <polyline points="3 6 5 6 21 6"></polyline>
                                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                        </svg>
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
