import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { token } from './lib/api'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { RepositoryDetail, RepositoryList } from './pages/Repositories'
import { PullRequestQueue, ReviewWorkspace } from './pages/PullRequests'
import { Approvals, FailedJobs, GithubIntegration, ReviewHistory } from './pages/Operations'
import { QualityAnalytics, SecurityDashboard } from './pages/Analytics'
import { AuditLogs, Configuration } from './pages/Admin'

function Protected() {
  return token() ? <Layout /> : <Navigate to="/login" replace />
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<Login />} />
    <Route element={<Protected />}>
      <Route path="/" element={<Dashboard />} />
      <Route path="/repositories" element={<RepositoryList />} />
      <Route path="/repositories/:id" element={<RepositoryDetail />} />
      <Route path="/pull-requests" element={<PullRequestQueue />} />
      <Route path="/pull-requests/:id" element={<ReviewWorkspace />} />
      <Route path="/approvals" element={<Approvals />} />
      <Route path="/history" element={<ReviewHistory />} />
      <Route path="/failed-jobs" element={<FailedJobs />} />
      <Route path="/security" element={<SecurityDashboard />} />
      <Route path="/analytics" element={<QualityAnalytics />} />
      <Route path="/audit" element={<AuditLogs />} />
      <Route path="/github" element={<GithubIntegration />} />
      <Route path="/configuration" element={<Configuration />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
}
