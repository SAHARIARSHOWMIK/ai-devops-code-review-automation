import { AlertTriangle, CheckCircle2, Clock3, GitPullRequest, Layers3, Radar, ShieldAlert, Sparkles } from 'lucide-react'
import { useApi } from '../lib/hooks'
import { ErrorBox, Loading, MetricCard, PageHeader, Panel, RiskPill, StatusBadge } from '../components/UI'
import type { PullRequest, Repository } from '../lib/types'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const overview = useApi<any>('/analytics/overview', {})
  const prs = useApi<PullRequest[]>('/pull-requests', [])
  const repos = useApi<Repository[]>('/repositories', [])
  if (overview.loading || prs.loading || repos.loading) return <Loading />
  if (overview.error) return <ErrorBox message={overview.error}/>
  const data=overview.data
  return <>
    <PageHeader eyebrow="Engineering intelligence" title="Engineering overview" description="A single view of repository health, review workload, security risk, and human decisions." actions={<Link to="/pull-requests" className="primary-button">Open review queue</Link>}/>
    <div className="metrics-grid four">
      <MetricCard label="Connected repositories" value={data.connected_repositories} helper="All webhooks healthy" icon={Layers3} tone="blue"/>
      <MetricCard label="Open pull requests" value={data.open_pull_requests} helper={`${data.awaiting_approval} awaiting approval`} icon={GitPullRequest} tone="purple"/>
      <MetricCard label="High-risk pull requests" value={data.high_risk_pull_requests} helper="Security review required" icon={ShieldAlert} tone="red"/>
      <MetricCard label="Published reviews" value={data.published_reviews} helper="Human approved" icon={CheckCircle2} tone="green"/>
    </div>
    <div className="dashboard-grid">
      <Panel title="Pull requests requiring attention" subtitle="Prioritized by risk and review status" className="span-2">
        <div className="table-wrap"><table><thead><tr><th>Pull request</th><th>Repository</th><th>Risk</th><th>Status</th><th>Reviewer</th></tr></thead><tbody>
          {prs.data.slice(0,5).map(pr=><tr key={pr.id}><td><Link className="table-title" to={`/pull-requests/${pr.id}`}>#{pr.github_number} {pr.title}</Link><span className="muted">{pr.changed_files_count} files · +{pr.additions} −{pr.deletions}</span></td><td>{pr.repository}</td><td><RiskPill score={pr.risk_score} level={pr.risk_level}/></td><td><StatusBadge value={pr.review_status}/></td><td>{pr.assigned_reviewer || 'Unassigned'}</td></tr>)}
        </tbody></table></div>
      </Panel>
      <Panel title="Risk distribution" subtitle="Current open pull requests">
        <div className="risk-bars">{(data.risk_distribution||[]).map((item:any)=><div key={item.name}><div><span>{item.name}</span><strong>{item.value}</strong></div><div className="bar-track"><i className={item.name.toLowerCase()} style={{width:`${Math.max(8,item.value/Math.max(data.open_pull_requests,1)*100)}%`}}/></div></div>)}</div>
        <div className="signal-card"><Radar size={19}/><div><strong>Most common signal</strong><span>{data.most_common_category || 'No findings yet'}</span></div></div>
      </Panel>
      <Panel title="Connected repositories" subtitle="Profiles and live synchronization">
        <div className="repo-mini-list">{repos.data.slice(0,4).map(repo=><Link to={`/repositories/${repo.id}`} key={repo.id}><div className="repo-avatar">{repo.primary_language.slice(0,2).toUpperCase()}</div><div><strong>{repo.full_name}</strong><span>{repo.active_review_profile.replaceAll('_',' ')}</span></div><StatusBadge value={repo.connection_status}/></Link>)}</div>
      </Panel>
      <Panel title="Review operations" subtitle="Automation and quality signals">
        <div className="operations-grid"><div><Clock3/><strong>{data.average_review_duration_ms} ms</strong><span>Average analysis time</span></div><div><AlertTriangle/><strong>{data.failed_analysis_jobs}</strong><span>Failed jobs</span></div><div><Sparkles/><strong>{data.false_positive_rate}%</strong><span>False-positive rate</span></div><div><ShieldAlert/><strong>{data.critical_findings}</strong><span>Open critical findings</span></div></div>
      </Panel>
    </div>
  </>
}
