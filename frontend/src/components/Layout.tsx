import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Activity, AlertTriangle, BarChart3, Bell, Boxes, CheckSquare, ChevronRight,
  CircleUserRound, ClipboardCheck, Code2, FileClock, Github, LayoutDashboard,
  ListChecks, LogOut, ScrollText, Settings, ShieldCheck
} from 'lucide-react'
import { clearSession, currentUser } from '../lib/api'
import type { User } from '../lib/types'

const sections = [
  ['Overview', [
    { to: '/', label: 'Engineering overview', icon: LayoutDashboard },
    { to: '/pull-requests', label: 'Pull-request queue', icon: ListChecks },
    { to: '/approvals', label: 'Pending approvals', icon: ClipboardCheck },
  ]],
  ['Assets', [
    { to: '/repositories', label: 'Repositories', icon: Boxes },
    { to: '/history', label: 'Review history', icon: FileClock },
    { to: '/failed-jobs', label: 'Failed jobs', icon: AlertTriangle },
  ]],
  ['Insights', [
    { to: '/security', label: 'Security dashboard', icon: ShieldCheck },
    { to: '/analytics', label: 'Quality analytics', icon: BarChart3 },
    { to: '/audit', label: 'Audit logs', icon: ScrollText },
  ]],
  ['Platform', [
    { to: '/github', label: 'GitHub integration', icon: Github },
    { to: '/configuration', label: 'Configuration', icon: Settings },
  ]],
] as const

export default function Layout() {
  const navigate = useNavigate()
  const user = currentUser<User>()
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Code2 size={22} /></div>
          <div><strong>SentinelReview</strong><span>AI DevOps Platform</span></div>
        </div>
        <nav>
          {sections.map(([title, links]) => (
            <div className="nav-section" key={title}>
              <p>{title}</p>
              {links.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                  <Icon size={18} /><span>{label}</span>{to === '/approvals' && <em>3</em>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-card">
            <CircleUserRound size={34} />
            <div><strong>{user?.name || 'Demo User'}</strong><span>{user?.role?.replaceAll('_', ' ')}</span></div>
          </div>
          <button className="icon-button" title="Sign out" onClick={() => { clearSession(); navigate('/login') }}><LogOut size={18} /></button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><Activity size={17} /> Engineering workspace <ChevronRight size={15} /> Acme Engineering</div>
          <div className="topbar-actions">
            <span className="live-dot">Live</span>
            <button className="icon-button" title="Notifications"><Bell size={19} /><i /></button>
          </div>
        </header>
        <section className="content"><Outlet /></section>
      </main>
    </div>
  )
}
