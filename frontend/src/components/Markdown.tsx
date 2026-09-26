// Renders post Markdown safely: raw HTML is never rendered, and the output is sanitized.
import ReactMarkdown, { type Components } from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

const components: Components = {
  // External links open in a new tab without handing the new page a reference to this one.
  a: ({ href, children }) => {
    const external = href !== undefined && /^https?:\/\//.test(href)
    return (
      <a
        href={href}
        {...(external && { target: '_blank', rel: 'noopener noreferrer nofollow ugc' })}
      >
        {children}
      </a>
    )
  },
  img: ({ src, alt }) => (
    <img
      src={typeof src === 'string' ? src : undefined}
      alt={alt ?? ''}
      loading="lazy"
      referrerPolicy="no-referrer"
    />
  ),
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose prose-lg max-w-none prose-invert prose-headings:font-display prose-a:text-plasma prose-code:rounded prose-code:bg-white/10 prose-code:px-1 prose-code:before:content-none prose-code:after:content-none prose-pre:glass prose-img:rounded-xl">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
