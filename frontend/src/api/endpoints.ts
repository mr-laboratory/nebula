// One typed function per API endpoint used by the UI.
import { request } from './client'
import type {
  Comment,
  CommentPage,
  FeedFilters,
  LikeStatus,
  LoginBody,
  Me,
  PostDetail,
  PostPage,
  RegisterBody,
  TagCount,
  TokenResponse,
} from './types'

export const api = {
  register: (body: RegisterBody) => request<Me>('/auth/register', { method: 'POST', body }),
  login: (body: LoginBody) => request<TokenResponse>('/auth/login', { method: 'POST', body }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  me: () => request<Me>('/users/me'),

  feed: (filters: FeedFilters) => request<PostPage>('/posts', { query: filters }),
  post: (slug: string) => request<PostDetail>(`/posts/${encodeURIComponent(slug)}`),
  tags: (limit = 12) => request<TagCount[]>('/tags', { query: { limit } }),

  like: (postId: string) => request<LikeStatus>(`/posts/${postId}/like`, { method: 'PUT' }),
  unlike: (postId: string) => request<LikeStatus>(`/posts/${postId}/like`, { method: 'DELETE' }),

  comments: (postId: string, offset: number, limit = 20) =>
    request<CommentPage>(`/posts/${postId}/comments`, { query: { offset, limit } }),
  addComment: (postId: string, body: string) =>
    request<Comment>(`/posts/${postId}/comments`, { method: 'POST', body: { body } }),
  editComment: (commentId: string, body: string) =>
    request<Comment>(`/comments/${commentId}`, { method: 'PATCH', body: { body } }),
  deleteComment: (commentId: string) =>
    request<void>(`/comments/${commentId}`, { method: 'DELETE' }),
}

export const keys = {
  feed: (filters: FeedFilters) => ['posts', filters] as const,
  post: (slug: string) => ['post', slug] as const,
  tags: ['tags'] as const,
  comments: (postId: string) => ['comments', postId] as const,
}
