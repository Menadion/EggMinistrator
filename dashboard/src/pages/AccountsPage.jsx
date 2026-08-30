import { Clipboard, Plus, RefreshCw, RotateCcw, UserCheck, UserMinus, Users, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { PageHeader, SearchInput } from '../components/Ui'

const emptyAccount = {
  firstName: '',
  middleInitial: '',
  lastName: '',
  username: '',
  role: 'inspector',
}
const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat('en-PH', {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: 'Asia/Manila',
      }).format(new Date(value))
    : 'Never'
const statusClass = (isActive) =>
  isActive ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-700'
const roleClass = { admin: 'bg-violet-100 text-violet-800', inspector: 'bg-sky-100 text-sky-800' }
const roleLabel = (role) => (role === 'admin' ? 'Admin' : 'Inspector')

function Modal({ title, children, onClose }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-3 sm:p-4">
      <button
        aria-label="Close dialog"
        className="absolute inset-0 bg-slate-950/45"
        onClick={onClose}
      />
      <section
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative max-h-[calc(100dvh-1.5rem)] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-4 shadow-2xl sm:max-h-[90vh] sm:p-6"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <h2 className="text-xl font-bold text-slate-900">{title}</h2>
          <button
            aria-label="Close dialog"
            onClick={onClose}
            className="grid min-h-11 min-w-11 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </section>
    </div>
  )
}

function NameFields({ account }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-slate-700">First Name</span>
          <input
            required
            name="firstName"
            defaultValue={account.firstName || ''}
            className="w-full rounded-lg border border-slate-200 px-3 py-2"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-slate-700">
            Middle Initial <span className="font-normal text-slate-400">(optional)</span>
          </span>
          <input
            name="middleInitial"
            defaultValue={account.middleInitial || ''}
            maxLength="2"
            pattern="[A-Za-z]\.?"
            title="Use one alphabetic character"
            className="w-full rounded-lg border border-slate-200 px-3 py-2"
          />
        </label>
      </div>
      <label className="block">
        <span className="mb-1 block text-sm font-semibold text-slate-700">Last Name</span>
        <input
          required
          name="lastName"
          defaultValue={account.lastName || ''}
          className="w-full rounded-lg border border-slate-200 px-3 py-2"
        />
      </label>
    </>
  )
}

export default function AccountsPage() {
  const { authenticatedFetch, user: currentUser } = useAuth()
  const [accounts, setAccounts] = useState([])
  const [summary, setSummary] = useState({ total: 0, active: 0, inactive: 0 })
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const [notice, setNotice] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const loadAccounts = async (filters = {}) => {
    setIsLoading(true)
    setError('')
    try {
      const selectedPage = filters.page ?? page
      const selectedSearch = filters.search ?? search
      const selectedRole = filters.role ?? role
      const selectedStatus = filters.status ?? status
      const query = new URLSearchParams({ page: String(selectedPage), pageSize: '10' })
      if (selectedSearch.trim()) query.set('search', selectedSearch.trim())
      if (selectedRole) query.set('role', selectedRole)
      if (selectedStatus) query.set('status', selectedStatus)
      const response = await authenticatedFetch(`/api/admin/accounts?${query}`)
      const result = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(result.error || 'Unable to load accounts.')
      setAccounts(result.accounts)
      setSummary(result.summary)
      setTotal(result.total)
    } catch (requestError) {
      setError(requestError.message || 'Unable to load accounts.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadAccounts()
  }, [page, role, status])

  const submitFilters = (event) => {
    event.preventDefault()
    setPage(1)
    loadAccounts({ page: 1 })
  }
  const resetFilters = () => {
    setSearch('')
    setRole('')
    setStatus('')
    setPage(1)
    loadAccounts({ search: '', role: '', status: '', page: 1 })
  }
  const closeModal = () => {
    setModal(null)
    setIsSaving(false)
    setError('')
  }

  const request = async (path, options) => {
    const response = await authenticatedFetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(result.error || 'Unable to complete the account action.')
    return result
  }

  const saveAccount = async (event, type) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const payload = {
      firstName: data.get('firstName'),
      middleInitial: data.get('middleInitial'),
      lastName: data.get('lastName'),
      username: data.get('username'),
      role: data.get('role'),
    }
    setIsSaving(true)
    setError('')
    try {
      if (type === 'add') {
        const result = await request('/api/admin/accounts', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setModal({
          type: 'temporary-password',
          account: result.user,
          temporaryPassword: result.temporaryPassword,
          expiresAt: result.temporaryPasswordExpiresAt,
        })
      } else {
        await request(`/api/admin/accounts/${modal.account.id}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        })
        closeModal()
        setNotice('Account updated successfully.')
        loadAccounts()
      }
    } catch (requestError) {
      setError(requestError.message || 'Unable to save the account.')
      setIsSaving(false)
    }
  }

  const confirmAction = async () => {
    const { action, account } = modal
    setIsSaving(true)
    setError('')
    try {
      if (action === 'reset') {
        const result = await request(`/api/admin/accounts/${account.id}/reset-password`, {
          method: 'POST',
          body: '{}',
        })
        setModal({
          type: 'temporary-password',
          account: result.user,
          temporaryPassword: result.temporaryPassword,
          expiresAt: result.temporaryPasswordExpiresAt,
        })
      } else {
        const isActive = action === 'reactivate'
        await request(`/api/admin/accounts/${account.id}/status`, {
          method: 'PATCH',
          body: JSON.stringify({ isActive }),
        })
        closeModal()
        setNotice(`Account ${isActive ? 'reactivated' : 'deactivated'} successfully.`)
        loadAccounts()
      }
    } catch (requestError) {
      setError(requestError.message || 'Unable to complete the account action.')
      setIsSaving(false)
    }
  }

  const copyTemporaryPassword = async () => {
    try {
      await navigator.clipboard.writeText(modal.temporaryPassword)
      setNotice('Temporary password copied. Deliver it through your approved internal method.')
    } catch {
      setError(
        'Unable to copy the temporary password. Copy it manually before closing this dialog.'
      )
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / 10))

  return (
    <div>
      <PageHeader
        title="Accounts"
        actions={
          <button
            onClick={() => {
              setError('')
              setModal({ type: 'add', account: emptyAccount })
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-forest-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-forest-900"
          >
            <Plus size={17} />
            Add Account
          </button>
        }
      />
      {notice && (
        <div className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          <span>{notice}</span>
          <button onClick={() => setNotice('')} aria-label="Dismiss success message">
            <X size={16} />
          </button>
        </div>
      )}
      {error && !modal && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <section className="account-summary-grid">
        <AccountCount label="Total Accounts" value={summary.total} icon={Users} tone="green" />
        <AccountCount
          label="Active Accounts"
          value={summary.active || 0}
          icon={UserCheck}
          tone="green"
        />
        <AccountCount
          label="Inactive Accounts"
          value={summary.inactive || 0}
          icon={UserMinus}
          tone="red"
        />
      </section>
      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
        <form
          onSubmit={submitFilters}
          className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_180px_auto]"
        >
          <SearchInput
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search employee name or username"
          />
          <select
            aria-label="Filter by role"
            value={role}
            onChange={(event) => {
              setRole(event.target.value)
              setPage(1)
            }}
            className="min-h-11 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="inspector">Inspector</option>
          </select>
          <select
            aria-label="Filter by account status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
            className="min-h-11 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <div className="flex flex-col gap-2 sm:flex-row">
            <button className="min-h-11 rounded-lg bg-forest-800 px-3 py-2 text-sm font-semibold text-white hover:bg-forest-900">
              Search
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <RotateCcw size={15} />
              Reset
            </button>
          </div>
        </form>
      </section>
      <section className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-[860px] w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                {['Employee Name', 'Username', 'Role', 'Status', 'Last Login', 'Actions'].map(
                  (heading) => (
                    <th key={heading} className="px-4 py-3 font-semibold">
                      {heading}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr>
                  <td colSpan="6" className="px-4 py-12 text-center text-slate-500">
                    <RefreshCw className="mx-auto mb-2 animate-spin" size={20} />
                    Loading accounts…
                  </td>
                </tr>
              )}
              {!isLoading && accounts.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-4 py-12 text-center text-slate-500">
                    No accounts match the selected filters.
                  </td>
                </tr>
              )}
              {accounts.map((account) => (
                <tr key={account.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold text-slate-800">
                    {account.fullName}
                    {account.id === currentUser?.id && (
                      <span className="ml-2 text-xs font-medium text-slate-400">You</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{account.username}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${roleClass[account.role]}`}
                    >
                      {roleLabel(account.role)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(account.isActive)}`}
                    >
                      {account.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(account.lastLoginAt)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setModal({ type: 'details', account })}
                        className="rounded border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        View
                      </button>
                      <button
                        onClick={() => {
                          setError('')
                          setModal({ type: 'edit', account })
                        }}
                        className="rounded border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setModal({ type: 'confirm', action: 'reset', account })}
                        className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100"
                      >
                        Reset Password
                      </button>
                      <button
                        onClick={() =>
                          setModal({
                            type: 'confirm',
                            action: account.isActive ? 'deactivate' : 'reactivate',
                            account,
                          })
                        }
                        className={`rounded border px-2 py-1 text-xs font-semibold ${account.isActive ? 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100' : 'border-green-200 bg-green-50 text-green-800 hover:bg-green-100'}`}
                      >
                        {account.isActive ? 'Deactivate' : 'Reactivate'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > 10 && (
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
            <span>
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((current) => current - 1)}
                className="rounded border border-slate-200 px-3 py-1.5 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((current) => current + 1)}
                className="rounded border border-slate-200 px-3 py-1.5 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>
      {(modal?.type === 'add' || modal?.type === 'edit') && (
        <Modal
          title={modal.type === 'add' ? 'Add employee account' : 'Edit employee account'}
          onClose={closeModal}
        >
          <form onSubmit={(event) => saveAccount(event, modal.type)} className="space-y-4">
            {error && (
              <p
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {error}
              </p>
            )}
            <NameFields account={modal.account} />
            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-slate-700">Username</span>
              <input
                required
                name="username"
                defaultValue={modal.account.username}
                minLength="4"
                maxLength="50"
                pattern="[A-Za-z0-9._-]{4,50}"
                title="4 to 50 letters, numbers, periods, hyphens, or underscores"
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-slate-700">Role</span>
              <select
                name="role"
                defaultValue={modal.account.role}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
              >
                <option value="admin">Admin</option>
                <option value="inspector">Inspector</option>
              </select>
            </label>
            {modal.type === 'add' && (
              <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
                New accounts are created as Active and must change their temporary password on first
                sign-in.
              </p>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={closeModal}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                disabled={isSaving}
                className="rounded-lg bg-forest-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {isSaving ? 'Saving…' : modal.type === 'add' ? 'Create Account' : 'Save Changes'}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {modal?.type === 'details' && (
        <Modal title="Account Details" onClose={closeModal}>
          <section>
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
              Personal Information
            </h3>
            <dl className="mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2">
              {[
                ['First Name', modal.account.firstName || '—'],
                [
                  'Middle Initial',
                  modal.account.middleInitial ? `${modal.account.middleInitial}.` : '—',
                ],
                ['Last Name', modal.account.lastName || '—'],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {label}
                  </dt>
                  <dd className="mt-1 text-sm text-slate-800">{value}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section className="mt-6 border-t border-slate-200 pt-5">
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
              Account Information
            </h3>
            <dl className="mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2">
              {[
                ['Username', modal.account.username],
                ['Role', roleLabel(modal.account.role)],
                ['Status', modal.account.isActive ? 'Active' : 'Inactive'],
                ['Last Login', formatDate(modal.account.lastLoginAt)],
                ['Created At', formatDate(modal.account.createdAt)],
                ['Updated At', formatDate(modal.account.updatedAt)],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {label}
                  </dt>
                  <dd className="mt-1 text-sm text-slate-800">{value}</dd>
                </div>
              ))}
            </dl>
          </section>
        </Modal>
      )}
      {modal?.type === 'confirm' && (
        <Modal
          title={
            modal.action === 'reset'
              ? 'Reset employee password?'
              : `${modal.action === 'deactivate' ? 'Deactivate' : 'Reactivate'} account?`
          }
          onClose={closeModal}
        >
          <p className="text-sm leading-6 text-slate-600">
            {modal.action === 'reset'
              ? `A new temporary password will be generated for ${modal.account.fullName}. Their existing sessions will be invalidated.`
              : modal.action === 'deactivate'
                ? `${modal.account.fullName} will no longer be able to sign in. Existing sessions will be invalidated.`
                : `${modal.account.fullName} will be able to sign in again with their current password.`}
          </p>
          {error && (
            <p
              role="alert"
              className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </p>
          )}
          <div className="mt-6 flex justify-end gap-2">
            <button
              onClick={closeModal}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700"
            >
              Cancel
            </button>
            <button
              disabled={isSaving}
              onClick={confirmAction}
              className="rounded-lg bg-forest-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {isSaving ? 'Working…' : 'Confirm'}
            </button>
          </div>
        </Modal>
      )}
      {modal?.type === 'temporary-password' && (
        <Modal title="Temporary password generated" onClose={closeModal}>
          <p className="text-sm leading-6 text-slate-600">
            Username: <strong>{modal.account.username}</strong>
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Give these credentials through your approved internal method. The temporary password
            expires {formatDate(modal.expiresAt)}.
          </p>
          <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            This password is displayed only once. It is not stored in the browser or database as
            plain text.
          </p>
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <code className="min-w-0 flex-1 break-all text-sm font-bold text-slate-800">
              {modal.temporaryPassword}
            </code>
            <button
              onClick={copyTemporaryPassword}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              <Clipboard size={16} />
              Copy
            </button>
          </div>
          <button
            onClick={closeModal}
            className="mt-6 w-full rounded-lg bg-forest-800 px-4 py-2.5 text-sm font-semibold text-white"
          >
            I have delivered these credentials
          </button>
        </Modal>
      )}
    </div>
  )
}

function AccountCount({ label, value, icon: Icon, tone }) {
  const toneClass = tone === 'red' ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-700'
  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div>
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="mt-0.5 text-xl font-bold text-slate-900">{value}</p>
      </div>
      <div className={`grid h-8 w-8 place-items-center rounded-full ${toneClass}`}>
        <Icon size={17} strokeWidth={2.5} />
      </div>
    </div>
  )
}
