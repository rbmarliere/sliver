export interface User {
  email: string
  old_password: string
  password: string
  access_key: string
  expires_at: number
  telegram: string
  max_risk: number
  cash_reserve: number
  target_factor: number
}
