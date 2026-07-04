'use client';
import { create } from 'zustand';
import type { AuthState, TheMUser } from '@/types/auth';

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid credentials');
      }
      const me = await fetch('/api/auth/me');
      if (!me.ok) throw new Error('Failed to load user');
      const user: TheMUser = await me.json();
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (e: any) {
      set({ user: null, isAuthenticated: false, isLoading: false, error: e.message });
      throw e;
    }
  },

  logout: async () => {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    set({ user: null, isAuthenticated: false, error: null });
  },

  fetchUser: async () => {
    try {
      const res = await fetch('/api/auth/me');
      if (!res.ok) {
        set({ user: null, isAuthenticated: false, isLoading: false });
        return false;
      }
      const user: TheMUser = await res.json();
      set({ user, isAuthenticated: true, isLoading: false });
      return true;
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return false;
    }
  },

  clearError: () => set({ error: null }),
}));
