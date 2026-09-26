// One typed function per API endpoint used by the UI.
import { request } from './client'
import type {
  Comment,
  CommentPage,
  FeedFilters,
  LikeStatus,
  LoginBody,
  Me,
  MyPostFilters,
  PostCreate,
  PostDetail,
  PostPage,
  PostUpdate,
  Profile,
  ProfileUpdate,
  RegisterBody,
  TagCount,
  TokenResponse,
} from './types'

export const api = {
  register: (body: RegisterBody) => request<Me>('/auth/register', { method: 'POST', body }),
  login: (body: LoginBody) => request<TokenResponse>('/auth/login', { method: 'POST', body }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  me: () => request<Me>('/users/me'),
  updateMe: (body: ProfileUpdate) => request<Me>('/users/me', { method: 'PATCH', body }),
  user: (username: string) => request<Profile>(`/users/${encodeURIComponent(username)}`),

  feed: (filters: FeedFilters) => request<PostPage>('/posts', { query: filters }),
  post: (slug: string) => request<PostDetail>(`/posts/${encodeURIComponent(slug)}`),
  myPosts: (filters: MyPostFilters) => request<PostPage>('/users/me/posts', { query: filters }),
  createPost: (body: PostCreate) => request<PostDetail>('/posts', { method: 'POST', body }),
  updatePost: (postId: string, body: PostUpdate) =>
    request<PostDetail>(`/posts/${postId}`, { method: 'PATCH', body }),
  publish: (postId: string) => request<PostDetail>(`/posts/${postId}/publish`, { method: 'POST' }),
  unpublish: (postId: string) =>
    request<PostDetail>(`/posts/${postId}/unpublish`, { method: 'POST' }),
  deletePost: (postId: string) => request<void>(`/posts/${postId}`, { method: 'DELETE' }),
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

// Every post list lives under ['posts'], so one invalidation refreshes feeds, profiles and the
// dashboard after any write.
export const keys = {
  feed: (filters: FeedFilters) => ['posts', filters] as const,
  myPosts: (filters: MyPostFilters) => ['posts', 'mine', filters] as const,
  user: (username: string) => ['user', username] as const,
  post: (slug: string) => ['post', slug] as const,
  tags: ['tags'] as const,
  comments: (postId: string) => ['comments', postId] as const,
}
