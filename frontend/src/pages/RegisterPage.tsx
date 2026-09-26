// Account creation form, with the API's validation messages shown next to each field.
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'

import { ApiError, describeError } from '@/api/errors'
import type { RegisterBody } from '@/api/types'
import { useAuth } from '@/auth/context'
import { Button } from '@/components/ui/button'
import { TextField } from '@/components/ui/field'
import { AuthShell } from '@/pages/AuthShell'
import { safeNext } from '@/lib/utils'

type Errors = Partial<Record<keyof RegisterBody, string>>

export function RegisterPage() {
  const { me, signUp } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const [fieldErrors, setFieldErrors] = useState<Errors>({})
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  if (me) return <Navigate to={next} replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const body: RegisterBody = {
      email: String(form.get('email')),
      username: String(form.get('username')).trim().toLowerCase(),
      display_name: String(form.get('display_name')).trim(),
      password: String(form.get('password')),
    }
    setPending(true)
    setError(null)
    setFieldErrors({})
    try {
      await signUp(body)
      void navigate(next, { replace: true })
    } catch (err) {
      const fields = err instanceof ApiError ? err.fieldMessages() : {}
      setFieldErrors(fields)
      if (Object.keys(fields).length === 0) setError(describeError(err))
    } finally {
      setPending(false)
    }
  }

  return (
    <AuthShell
      title="Join Nebula"
      subtitle="Where ideas take shape."
      footer={
        <>
          Already have an account?{' '}
          <Link
            to={`/login?next=${encodeURIComponent(next)}`}
            className="text-plasma hover:underline"
          >
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <TextField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          error={fieldErrors.email}
          hint="Private: never shown on your profile."
        />
        <TextField
          label="Username"
          name="username"
          autoComplete="username"
          required
          minLength={3}
          maxLength={30}
          pattern="[a-z0-9_]+"
          error={fieldErrors.username}
          hint="3–30 characters: a–z, 0–9 and underscores."
        />
        <TextField
          label="Display name"
          name="display_name"
          autoComplete="name"
          required
          maxLength={60}
          error={fieldErrors.display_name}
        />
        <TextField
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          error={fieldErrors.password}
          hint="At least 12 characters. A passphrase works well."
        />
        {error && (
          <p className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <Button type="submit" variant="primary" size="lg" className="w-full" loading={pending}>
          Create account
        </Button>
      </form>
    </AuthShell>
  )
}
