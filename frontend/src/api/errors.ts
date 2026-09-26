// ApiError: RFC 9457 problem details from the API, turned into something the UI can show.

export type FieldError = { loc: (string | number)[]; msg: string; type: string }

type Problem = {
  title?: string
  status?: number
  detail?: string
  errors?: FieldError[]
}

export class ApiError extends Error {
  readonly status: number
  readonly title: string
  readonly fieldErrors: FieldError[]
  readonly retryAfter: number | null

  constructor(status: number, problem: Problem, retryAfter: number | null = null) {
    super(problem.detail ?? problem.title ?? `Request failed (${status})`)
    this.name = 'ApiError'
    this.status = status
    this.title = problem.title ?? 'Error'
    this.fieldErrors = problem.errors ?? []
    this.retryAfter = retryAfter
  }

  /** Validation messages keyed by body field name, e.g. `{ password: "..." }`. */
  fieldMessages(): Record<string, string> {
    const messages: Record<string, string> = {}
    for (const error of this.fieldErrors) {
      const field = error.loc[0] === 'body' ? error.loc[1] : undefined
      if (typeof field === 'string' && !(field in messages)) {
        messages[field] = error.msg.replace(/^Value error, /, '')
      }
    }
    return messages
  }
}

export async function toApiError(response: Response): Promise<ApiError> {
  let problem: Problem = {}
  try {
    problem = (await response.json()) as Problem
  } catch {
    // Not JSON (e.g. a proxy error page): fall back to the status code alone.
  }
  const retryAfter = Number(response.headers.get('Retry-After')) || null
  return new ApiError(response.status, problem, retryAfter)
}

/** A short, human message for any error thrown by a request. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429 && error.retryAfter) {
      return `Too many attempts. Try again in ${error.retryAfter} seconds.`
    }
    if (error.status >= 500) return 'Something went wrong on our side. Please try again.'
    return error.message
  }
  return 'Could not reach the server. Check your connection and try again.'
}
