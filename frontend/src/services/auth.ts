import { API_BASE_URL } from './apiConfig'

export type UserRole = 'admin' | 'employee'

export interface AuthIdentity {
  employee_id: string
  role: UserRole
}

interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  employee_id: string
  role: UserRole
}

const TOKEN_STORAGE_KEY = 'cloudmentor.access_token'

function isUserRole(value: unknown): value is UserRole {
  return value === 'admin' || value === 'employee'
}

function decodeTokenPayload(token: string): Record<string, unknown> | null {
  const parts = token.split('.')

  if (parts.length !== 3) {
    return null
  }

  try {
    const normalized = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/')
    const padded = normalized.padEnd(
      normalized.length + ((4 - (normalized.length % 4)) % 4),
      '=',
    )
    const json = decodeURIComponent(
      Array.from(atob(padded))
        .map(
          (character) => (
            `%${character.charCodeAt(0).toString(16).padStart(2, '0')}`
          ),
        )
        .join(''),
    )

    const payload: unknown = JSON.parse(json)

    return (
      typeof payload === 'object' && payload !== null
        ? payload as Record<string, unknown>
        : null
    )
  } catch {
    return null
  }
}

export function getAccessToken(): string | null {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)

  if (!token) {
    return null
  }

  const payload = decodeTokenPayload(token)
  const expiresAt = payload?.exp

  if (
    typeof expiresAt !== 'number'
    || expiresAt * 1000 <= Date.now()
  ) {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    return null
  }

  return token
}

export function getIdentity(): AuthIdentity | null {
  const token = getAccessToken()

  if (!token) {
    return null
  }

  const payload = decodeTokenPayload(token)
  const employeeId = payload?.sub
  const role = payload?.role

  if (
    typeof employeeId !== 'string'
    || !employeeId
    || !isUserRole(role)
  ) {
    return null
  }

  return {
    employee_id: employeeId,
    role,
  }
}

export async function login(
  employeeId: string,
  password: string,
): Promise<AuthIdentity> {
  const body = new URLSearchParams({
    username: employeeId,
    password,
  })

  const response = await fetch(`${API_BASE_URL}/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  })

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Mã nhân viên hoặc mật khẩu không đúng')
    }
    throw new Error('Không thể đăng nhập. Vui lòng thử lại.')
  }

  const payload: TokenResponse = await response.json()

  if (
    typeof payload.access_token !== 'string'
    || !isUserRole(payload.role)
  ) {
    throw new Error('Phản hồi đăng nhập không hợp lệ')
  }

  localStorage.setItem(
    TOKEN_STORAGE_KEY,
    payload.access_token,
  )

  const identity = getIdentity()

  if (!identity) {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    throw new Error('Token đăng nhập không hợp lệ')
  }

  return identity
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}
