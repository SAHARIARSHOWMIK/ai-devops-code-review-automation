import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, CheckCircle2, Code2, Github, LockKeyhole, ShieldCheck, Sparkles } from 'lucide-react'
import { post, setSession } from '../lib/api'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@demo.com')
  const [password, setPassword] = useState('demo1234')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const result = await post<any>('/auth/login', { email, password })
      setSession(result.access_token, result.user)
      navigate('/')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in') }
    finally { setBusy(false) }
  }
  return <div className="login-page">
    <div className="login-visual">
      <div className="brand large"><div className="brand-mark"><Code2 size={24} /></div><div><strong>SentinelReview</strong><span>AI DevOps Platform</span></div></div>
      <div className="login-copy"><p className="eyebrow">Repository-aware engineering intelligence</p><h1>Ship safer code without replacing human judgment.</h1><p>Combine deterministic analyzers, structured AI review, risk scoring, human approval, GitHub publishing, re-analysis, and engineering analytics.</p></div>
      <div className="feature-stack">
        <div><ShieldCheck /><span><strong>Evidence-based findings</strong>Files, lines, confidence, and normalized analyzer sources.</span></div>
        <div><Github /><span><strong>GitHub-native workflow</strong>Signed webhooks, pull-request context, review comments, and version tracking.</span></div>
        <div><Sparkles /><span><strong>Human-controlled AI</strong>Approve, edit, dismiss, suppress, or keep findings internal.</span></div>
      </div>
      <div className="login-orbit orbit-one"/><div className="login-orbit orbit-two"/>
    </div>
    <div className="login-form-area"><form className="login-card" onSubmit={submit}>
      <div className="lock-icon"><LockKeyhole /></div><h2>Welcome back</h2><p>Sign in to your engineering review workspace.</p>
      <label>Email address<input value={email} onChange={e => setEmail(e.target.value)} type="email" required /></label>
      <label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" required /></label>
      {error && <div className="error-box">{error}</div>}
      <button className="primary-button wide" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}<ArrowRight size={18}/></button>
      <div className="demo-box"><CheckCircle2 size={18}/><div><strong>Portfolio demo account</strong><span>admin@demo.com · demo1234</span></div></div>
      <small className="login-note">Demo mode uses controlled sample repositories. Live GitHub publishing requires your own GitHub App credentials.</small>
    </form></div>
  </div>
}
