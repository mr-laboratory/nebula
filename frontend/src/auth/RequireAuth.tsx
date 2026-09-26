// Route guard: signed-out visitors are sent to sign-in and brought back afterwards.
import { Navigate, Outlet, useLocation } from 'react-router'

import { useAuth } from './context'

export function RequireAuth() {
  const { me } = useAuth()
  const location = useLocation()
  if (!me) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return <Outlet />
}
