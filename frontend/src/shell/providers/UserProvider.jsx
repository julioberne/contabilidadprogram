import { createContext, useContext, useMemo } from 'react';

const UserContext = createContext(null);

export function UserProvider({ user, logout, children }) {
  const value = useMemo(() => ({
    user,
    logout,
    isAdmin: user?.role === 'ADMIN',
    userId: user?.id || null,
    userName: user?.name || 'Usuario',
    userEmail: user?.email || '',
    userInitials: user?.initials || 'U',
    // Prepared for multi-workspace
    workspaceId: 'default',
    workspaceName: 'HOLDING PRINCIPAL',
  }), [user, logout]);

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) {
    // Return safe defaults if used outside provider
    return {
      user: null, logout: () => {}, isAdmin: false,
      userId: null, userName: 'Usuario', userEmail: '',
      userInitials: 'U', workspaceId: 'default',
      workspaceName: 'HOLDING PRINCIPAL',
    };
  }
  return ctx;
}

export default UserProvider;
