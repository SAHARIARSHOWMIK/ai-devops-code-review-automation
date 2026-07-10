import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Clock3, Info, Loader2, ShieldAlert } from 'lucide-react'

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return <div className="page-header"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description && <p className="page-description">{description}</p>}</div>{actions && <div className="page-actions">{actions}</div>}</div>
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function SeverityBadge({ value }: { value: string }) {
  return <Badge tone={value.toLowerCase()}>{value}</Badge>
}

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase()
  const tone = normalized.includes('fail') || normalized.includes('critical') ? 'critical' : normalized.includes('publish') || normalized.includes('complete') || normalized.includes('active') || normalized.includes('approved') ? 'success' : normalized.includes('await') || normalized.includes('pending') || normalized.includes('running') ? 'warning' : 'neutral'
  return <Badge tone={tone}>{value.replaceAll('_', ' ')}</Badge>
}

export function RiskPill({ score, level }: { score: number; level: string }) {
  return <div className={`risk-pill ${level}`}><strong>{score}</strong><span>{level}</span></div>
}

export function MetricCard({ label, value, helper, icon: Icon, tone = 'blue' }: { label: string; value: ReactNode; helper?: string; icon: any; tone?: string }) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={20} /></div><div><span>{label}</span><strong>{value}</strong>{helper && <small>{helper}</small>}</div></div>
}

export function Panel({ title, subtitle, children, action, className = '' }: { title?: string; subtitle?: string; children: ReactNode; action?: ReactNode; className?: string }) {
  return <div className={`panel ${className}`}>{(title || action) && <div className="panel-header"><div>{title && <h3>{title}</h3>}{subtitle && <p>{subtitle}</p>}</div>{action}</div>}<div className="panel-body">{children}</div></div>
}

export function Empty({ title, text }: { title: string; text: string }) {
  return <div className="empty"><Info size={28} /><strong>{title}</strong><span>{text}</span></div>
}

export function Loading() { return <div className="loading"><Loader2 className="spin" /> Loading workspace data…</div> }
export function ErrorBox({ message }: { message: string }) { return <div className="error-box"><AlertCircle size={18} /> {message}</div> }

export function RiskGauge({ score }: { score: number }) {
  const color = score >= 75 ? '#ef476f' : score >= 50 ? '#f59e0b' : score >= 25 ? '#38bdf8' : '#34d399'
  return <div className="gauge" style={{ background: `conic-gradient(${color} ${score * 3.6}deg, #182335 0deg)` }}><div><strong>{score}</strong><span>/ 100</span></div></div>
}

export function TimelineStatus({ status }: { status: string }) {
  const Icon = status.includes('failed') ? ShieldAlert : status.includes('running') ? Clock3 : status.includes('complete') || status.includes('publish') ? CheckCircle2 : Info
  return <span className="timeline-status"><Icon size={15} />{status.replaceAll('_', ' ')}</span>
}
