// Session state for the whole app: who is signed in, and sign-in / sign-up / sign-out actions.
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState, type ReactNode } from 'react'

import { hasSessionHint, onSessionChange, refresh, setSession } from '@/api/client'
import { api } from '@/api/endpoints'
import type { LoginBody, Me, ProfileUpdate, RegisterBody } from '@/api/types'
import { Splash } from '@/components/States'

import { AuthContext, type AuthState } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [me, setMe] = useState<Me | null>(null)
  const [ready, setReady] = useState(() => !hasSessionHint()) // no hint: nothing to restore

  // Restore the session on page load: a refresh cookie may still be valid.
  useEffect(() => {
    let cancelled = false
    async function restore() {
      if (hasSessionHint() && (await refresh())) {
        const profile = await api.me().catch(() => null)
        if (!cancelled) setMe(profile)
      }
      if (!cancelled) setReady(true)
    }
    void restore()
    return () => {
      cancelled = true
    }
  }, [])

  // If a refresh fails later (session revoked or expired), drop the user everywhere.
  useEffect(
    () =>
      onSessionChange((signedIn) => {
        if (!signedIn) {
          setMe(null)
          void queryClient.invalidateQueries()
        }
      }),
    [queryClient],
  )

  const actions = useMemo(() => {
    async function signIn(body: LoginBody) {
      const { access_token } = await api.login(body)
      setSession(access_token)
      setMe(await api.me())
      await queryClient.invalidateQueries() // liked_by_me and drafts depend on who is asking
    }
    async function signUp(body: RegisterBody) {
      await api.register(body)
      await signIn({ email: body.email, password: body.password })
    }
    async function signOut() {
      try {
        await api.logout()
      } finally {
        setSession(null)
        setMe(null)
        queryClient.clear()
      }
    }
    async function updateProfile(body: ProfileUpdate) {
      const updated = await api.updateMe(body)
      setMe(updated)
      // Display names appear on posts, comments and profiles.
      await queryClient.invalidateQueries({ queryKey: ['user', updated.username] })
      await queryClient.invalidateQueries({ queryKey: ['posts'] })
      await queryClient.invalidateQueries({ queryKey: ['post'] })
      await queryClient.invalidateQueries({ queryKey: ['comments'] })
    }
    return { signIn, signUp, signOut, updateProfile }
  }, [queryClient])

  const value = useMemo<AuthState>(() => ({ me, ready, ...actions }), [me, ready, actions])
  // Hold rendering until we know whether a session exists, so pages never flash "signed out".
  return <AuthContext value={value}>{ready ? children : <Splash />}</AuthContext>
}
