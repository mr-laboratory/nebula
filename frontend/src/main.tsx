// App entry: query cache, motion preferences, session restore and routes.
import '@/index.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MotionConfig } from 'motion/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'

import { ApiError } from '@/api/errors'
import { AuthProvider } from '@/auth/AuthProvider'
import { Layout } from '@/components/Layout'
import { FeedPage } from '@/pages/FeedPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // 4xx answers won't change on retry; network blips and 5xx might.
      retry: (failures, error) =>
        !(error instanceof ApiError && error.status < 500) && failures < 2,
    },
  },
})

// Pages other than the feed load on demand: the post page carries the Markdown pipeline, and
// most visitors never open the auth forms.
const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <FeedPage /> },
      {
        path: 'p/:slug',
        lazy: async () => ({ Component: (await import('@/pages/PostPage')).PostPage }),
      },
      {
        path: 'login',
        lazy: async () => ({ Component: (await import('@/pages/LoginPage')).LoginPage }),
      },
      {
        path: 'register',
        lazy: async () => ({ Component: (await import('@/pages/RegisterPage')).RegisterPage }),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

const root = document.getElementById('root')
if (!root) throw new Error('#root is missing from index.html')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </MotionConfig>
    </QueryClientProvider>
  </StrictMode>,
)
