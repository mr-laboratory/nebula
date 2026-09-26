// Sign-in form. Returns to the page that sent the user here (same-site paths only).
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'

import { describeError } from '@/api/errors'
import { useAuth } from '@/auth/context'
import { Button } from '@/components/ui/button'
import { TextField } from '@/components/ui/field'
import { AuthShell } from '@/pages/AuthShell'
import { safeNext } from '@/lib/utils'

export function LoginPage() {
  const { me, signIn } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  if (me) return <Navigate to={next} replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setPending(true)
    setError(null)
    try {
      await signIn({ email: String(form.get('email')), password: String(form.get('password')) })
      void navigate(next, { replace: true })
    } catch (err) {
      setError(describeError(err)) // the API answers the same for wrong email and wrong password
    } finally {
      setPending(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to write, like and comment."
      footer={
        <>
          New here?{' '}
          <Link
            to={`/register?next=${encodeURIComponent(next)}`}
            className="text-plasma hover:underline"
          >
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <TextField label="Email" name="email" type="email" autoComplete="email" required />
        <TextField
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
        {error && (
          <p className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <Button type="submit" variant="primary" size="lg" className="w-full" loading={pending}>
          Sign in
        </Button>
      </form>
    </AuthShell>
  )
}
