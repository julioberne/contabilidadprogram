import { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';

const STORAGE_KEY = 'finsys_notifications';
const MAX_NOTIFICATIONS = 50;

const NotificationContext = createContext(null);

// Generate unique ID
let _idCounter = Date.now();
const uid = () => String(++_idCounter);

export function NotificationProvider({ children }) {
  // Load from localStorage on mount
  const [notifications, setNotifications] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });

  // Persist to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications.slice(0, MAX_NOTIFICATIONS)));
    } catch { /* silent */ }
  }, [notifications]);

  // notify(message, type, module)
  // type: 'SUCCESS' | 'INFO' | 'WARNING' | 'ERROR'
  // module: 'contabilidad' | 'rrhh' | 'tower' | 'sistema' | etc.
  const notify = useCallback((message, type = 'INFO', module = 'sistema') => {
    const newNotif = {
      id: uid(),
      message,
      type,
      module,
      timestamp: new Date().toISOString(),
      read: false,
    };
    setNotifications(prev => [newNotif, ...prev].slice(0, MAX_NOTIFICATIONS));
  }, []);

  const markRead = useCallback((id) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const unreadCount = useMemo(() => notifications.filter(n => !n.read).length, [notifications]);

  const value = useMemo(() => ({
    notifications,
    notify,
    markRead,
    markAllRead,
    clearAll,
    unreadCount,
  }), [notifications, notify, markRead, markAllRead, clearAll, unreadCount]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotify() {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    return {
      notifications: [], notify: () => {}, markRead: () => {},
      markAllRead: () => {}, clearAll: () => {}, unreadCount: 0,
    };
  }
  return ctx;
}

export default NotificationProvider;
