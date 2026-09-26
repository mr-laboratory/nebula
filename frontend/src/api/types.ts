// Friendly names for the generated API schema types, so components never hand-write API shapes.
import type { components } from './schema'

type Schemas = components['schemas']

export type PostSummary = Schemas['PostSummary']
export type PostDetail = Schemas['PostDetail']
export type Comment = Schemas['CommentOut']
export type LikeStatus = Schemas['LikeStatus']
export type Me = Schemas['UserMe']
export type Author = Schemas['AuthorPublic']
export type Profile = Schemas['UserPublic']
export type ProfileUpdate = Schemas['UserUpdate']
export type PostCreate = Schemas['PostCreate']
export type PostUpdate = Schemas['PostUpdate']
export type PostStatus = Schemas['PostStatus']
export type TagCount = Schemas['TagCount']
export type RegisterBody = Schemas['RegisterRequest']
export type LoginBody = Schemas['LoginRequest']
export type TokenResponse = Schemas['TokenResponse']
export type PostPage = Schemas['Page_PostSummary_']
export type CommentPage = Schemas['Page_CommentOut_']

export type FeedFilters = {
  tag?: string
  author?: string
  q?: string
  sort?: 'newest' | 'oldest'
  limit?: number
  offset?: number
}

export type MyPostFilters = {
  status?: PostStatus
  limit?: number
  offset?: number
}
