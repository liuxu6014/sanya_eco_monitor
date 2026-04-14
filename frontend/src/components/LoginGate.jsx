import { useState } from 'react'
import { api } from '../utils/api.js'
import s from './LoginGate.module.css'

export default function LoginGate({ onSuccess }) {
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      const result = await api.authLogin(password)
      if (result?.authenticated) {
        setPassword('')
        onSuccess()
        return
      }
      setError('登录失败，请重试')
    } catch (err) {
      setError(err.message || '登录失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={s.shell}>
      <div className={s.backdropGlow} />
      <form className={s.card} onSubmit={handleSubmit}>
        <div className={s.badge}>平台访问验证</div>
        <h1 className={s.title}>三亚市天涯区橡胶林近自然化改造和农田提升监测平台</h1>
        <p className={s.subtitle}>请输入访问密码后进入平台。</p>

        <label className={s.label} htmlFor="platform-password">访问密码</label>
        <input
          id="platform-password"
          className={s.input}
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="请输入平台密码"
          autoComplete="current-password"
          disabled={submitting}
        />

        {error && <div className={s.error}>{error}</div>}

        <button className={s.button} type="submit" disabled={submitting || !password.trim()}>
          {submitting ? '验证中...' : '进入平台'}
        </button>
      </form>
    </div>
  )
}
