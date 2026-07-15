/** 通用 API 响应包装 */
export interface ApiResponse<T = unknown> {
  data: T
  detail?: string
}

/** 分页参数 */
export interface PaginationParams {
  page?: number
  page_size?: number
}
