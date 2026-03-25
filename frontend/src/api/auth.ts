import { api } from './client'

export interface User {
  id: number
  email: string
}

export const authApi = {
  me:       ()                                      => api.get<User>('/auth/me'),
  login:    (email: string, password: string)       => api.post<User>('/auth/login', { email, password }),
  register: (email: string, password: string)       => api.post<User>('/auth/register', { email, password }),
  logout:   ()                                      => api.post<void>('/auth/logout'),
  changePassword: (email: string, password: string) => api.put<void>('/auth/password', { email, password }),
}
