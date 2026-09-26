// 404 view for unknown routes and for posts that don't exist (or aren't visible to you).
import { Link } from 'react-router'

import { EmptyState } from '@/components/States'
import { buttonVariants } from '@/components/ui/button-variants'

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-lg py-10">
      <title>Not found · Nebula</title>
      <EmptyState title="Lost in space">
        <p className="mb-6">This page drifted out of orbit, or it was never here.</p>
        <Link to="/" className={buttonVariants({ variant: 'primary' })}>
          Back to the feed
        </Link>
      </EmptyState>
    </div>
  )
}
