// The auth context object and its hook, kept apart from the provider for fast refresh.
import { createContext, use } from 'react'

import type { LoginBody, Me, ProfileUpdate, RegisterBody } from '@/api/types'

export type AuthState = {
  me: Me | null
  ready: boolean
  signIn: (body: LoginBody) => Promise<void>
  signUp: (body: RegisterBody) => Promise<void>
  signOut: () => Promise<void>
  updateProfile: (body: ProfileUpdate) => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const auth = use(AuthContext)
  if (!auth) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}
