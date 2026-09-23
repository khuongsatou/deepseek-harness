import { useCallback, useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import { Button, IconSearchOutlineRegular, Modal } from '@deepseek-ai/dsh-client-ui-primitives'
import type { GithubRepositorySearchResult } from '@deepseek-ai/dsh-host-directory-picker/types'
import type { Translate } from '@deepseek-ai/dsh-client-locale/client'
import css from './ProjectSetupModal.module.css'

export interface ProjectSetupModalProps {
  open: boolean
  initialMode: 'create' | 'clone'
  basePath: string
  onClose: () => void
  onSuccess: (targetPath: string) => void
  createDirectory: (path: string, name: string) => Promise<string>
  cloneGit?: ((url: string, basePath: string, name?: string) => Promise<string>) | undefined
  searchGithub?: ((query: string) => Promise<GithubRepositorySearchResult[]>) | undefined
  t: Translate
}


export function ProjectSetupModal({
  open,
  initialMode,
  basePath,
  onClose,
  onSuccess,
  createDirectory,
  cloneGit,
  searchGithub,
  t,
}: ProjectSetupModalProps) {
  const [mode, setMode] = useState<'create' | 'clone'>(initialMode)
  const [destination, setDestination] = useState(basePath)
  const [projectName, setProjectName] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<GithubRepositorySearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const progressTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (open) {
      setMode(initialMode)
      setDestination(basePath)
      setProjectName('')
      setRepoUrl('')
      setSearchQuery('')
      setSearchResults([])
      setSearching(false)
      setHasSearched(false)
      setSearchError(null)
      setSubmitting(false)
      setProgress(0)
      setError(null)
    }
  }, [open, initialMode, basePath])

  const stopProgress = useCallback(() => {
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current)
      progressTimerRef.current = null
    }
  }, [])

  const startProgress = useCallback(() => {
    stopProgress()
    setProgress(0)
    progressTimerRef.current = window.setInterval(() => {
      setProgress((prev) => {
        if (prev >= 92) return prev
        const step = prev < 40 ? 8 : prev < 75 ? 4 : 2
        return Math.min(92, prev + step)
      })
    }, 450)
  }, [stopProgress])

  useEffect(() => {
    return () => { stopProgress() }
  }, [stopProgress])

  const handleSearch = async () => {
    const q = searchQuery.trim()
    if (!q || !searchGithub) return
    setSearching(true)
    setSearchError(null)
    try {
      const results = await searchGithub(q)
      setSearchResults(results)
      setHasSearched(true)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : String(err))
      setSearchResults([])
      setHasSearched(true)
    } finally {
      setSearching(false)
    }
  }

  const handleSubmit = async () => {
    if (submitting) return
    setError(null)

    const dest = destination.trim()
    if (!dest) {
      setError(t('browser.missingDestination') || 'Please enter a destination folder')
      return
    }

    if (mode === 'create') {
      const name = projectName.trim()
      if (!name) {
        setError(t('browser.missingProjectName') || 'Please enter a project name')
        return
      }
      setSubmitting(true)
      try {
        const createdPath = await createDirectory(dest, name)
        onSuccess(createdPath)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setSubmitting(false)
      }
    } else {
      const url = repoUrl.trim()
      if (!url) {
        setError(t('browser.missingRepoUrl') || 'Please enter a GitHub repository URL')
        return
      }
      if (!cloneGit) {
        setError('Host does not support cloneGit')
        return
      }
      setSubmitting(true)
      startProgress()
      try {
        const clonedPath = await cloneGit(url, dest)
        stopProgress()
        setProgress(100)
        await new Promise(r => window.setTimeout(r, 200))
        onSuccess(clonedPath)
      } catch (err) {
        stopProgress()
        setProgress(0)
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        stopProgress()
        setSubmitting(false)
      }
    }
  }

  if (!open) return null

  return (
    <Modal
      open={open}
      onClose={() => { if (!submitting) onClose() }}
      title={t('browser.createOrClone') || 'Create or clone project'}
      className={clsx(css.setupDialog)}
      headless
    >
      <div className={css.setupBody}>
        <div className={css.headerRow}>
          <h3 className={css.title}>{t('browser.createOrClone') || 'Create or clone project'}</h3>
          <Button variant="ghost" disabled={submitting} onClick={onClose}>
            {t('browser.cancel') || 'Cancel'}
          </Button>
        </div>

        <div className={css.modeTabs} role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'create'}
            disabled={submitting}
            className={clsx(css.modeTab, mode === 'create' && css.modeTabActive)}
            onClick={() => { setMode('create'); setError(null) }}
          >
            {t('browser.newProject') || 'New project'}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'clone'}
            disabled={submitting}
            className={clsx(css.modeTab, mode === 'clone' && css.modeTabActive)}
            onClick={() => { setMode('clone'); setError(null) }}
          >
            {t('browser.cloneGit') || 'Clone from GitHub'}
          </button>
        </div>

        <div className={css.field}>
          <span className={css.fieldLabel}>{t('browser.destination') || 'Destination folder'}</span>
          <input
            className={css.input}
            value={destination}
            disabled={submitting}
            onChange={e => setDestination(e.target.value)}
            placeholder="/path/to/projects"
          />
        </div>

        {mode === 'create' ? (
          <div className={css.field}>
            <span className={css.fieldLabel}>{t('browser.projectName') || 'Project name'}</span>
            <input
              className={css.input}
              value={projectName}
              disabled={submitting}
              autoFocus
              onChange={e => setProjectName(e.target.value)}
              placeholder="my-awesome-app"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  void handleSubmit()
                }
              }}
            />
          </div>
        ) : (
          <>
            <div className={css.field}>
              <span className={css.fieldLabel}>{t('browser.searchGithub') || 'Search GitHub'}</span>
              <div className={css.searchRow}>
                <div className={css.searchInputWrap}>
                  <IconSearchOutlineRegular size={16} className={css.searchIcon} />
                  <input
                    className={clsx(css.input, css.searchInput)}
                    value={searchQuery}
                    disabled={submitting || searching}
                    placeholder={t('browser.searchPlaceholder') || 'owner/repo or keywords'}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        void handleSearch()
                      }
                    }}
                  />
                </div>
                <Button
                  variant="outline"
                  disabled={submitting || searching || !searchQuery.trim()}
                  onClick={handleSearch}
                >
                  {searching ? (t('browser.searching') || 'Searching…') : (t('browser.searchButton') || 'Search')}
                </Button>
              </div>
            </div>

            {(searching || searchResults.length > 0 || (hasSearched && !searching) || searchError) && (
              <div className={css.searchResults}>
                {searching && <p className={css.searchStatus}>{t('browser.searching') || 'Searching GitHub…'}</p>}
                {searchError && <p className={css.searchStatus}>{searchError}</p>}
                {!searching && !searchError && searchResults.length === 0 && hasSearched && (
                  <p className={css.searchStatus}>{t('browser.noRepos') || 'No repositories found.'}</p>
                )}
                {!searching && searchResults.map(repo => (
                  <button
                    key={repo.fullName}
                    type="button"
                    className={css.searchResultItem}
                    disabled={submitting}
                    onClick={() => {
                      setRepoUrl(repo.cloneUrl || repo.htmlUrl)
                    }}
                  >
                    <div className={css.searchResultHeader}>
                      <span className={css.searchResultName}>{repo.fullName}</span>
                      <span className={css.searchResultMeta}>
                        {repo.language ? `${repo.language} · ` : ''}
                        ★ {repo.stars}
                      </span>
                    </div>
                    {repo.description && <p className={css.searchResultDesc}>{repo.description}</p>}
                  </button>
                ))}
              </div>
            )}

            <div className={css.field}>
              <span className={css.fieldLabel}>{t('browser.repoUrl') || 'GitHub repository URL'}</span>
              <input
                className={css.input}
                value={repoUrl}
                disabled={submitting}
                placeholder="https://github.com/owner/repo"
                onChange={e => setRepoUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleSubmit()
                  }
                }}
              />
            </div>
          </>
        )}

        {submitting && mode === 'clone' && (
          <div className={css.cloneProgressBox}>
            <div className={css.cloneProgressRow}>
              <span>{t('browser.cloning') || 'Cloning…'}</span>
              <span>{progress}%</span>
            </div>
            <div className={css.cloneProgressTrack}>
              <div className={css.cloneProgressFill} style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}

        {error && <div className={css.errorBox}>{error}</div>}

        <div className={css.actions}>
          <Button variant="outline" disabled={submitting} onClick={onClose}>
            {t('browser.cancel') || 'Cancel'}
          </Button>
          <Button
            variant="primary"
            disabled={submitting || (mode === 'create' ? !projectName.trim() : !repoUrl.trim())}
            onClick={handleSubmit}
          >
            {mode === 'create'
              ? (t('browser.createProjectAction') || 'Create Project')
              : (t('browser.cloneProjectAction') || 'Clone Project')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
