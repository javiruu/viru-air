"use client";

import { createContext, type ReactNode, useContext, useMemo } from "react";

export type AuthUser = {
  id: string;
  email: string;
  locale: string;
  is_admin: boolean;
};

type AuthContextValue = {
  user: AuthUser | null;
};

const AuthContext = createContext<AuthContextValue>({ user: null });

export function AuthProvider({
  user,
  children,
}: {
  user: AuthUser | null;
  children: ReactNode;
}) {
  const value = useMemo<AuthContextValue>(() => ({ user }), [user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
