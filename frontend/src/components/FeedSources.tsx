import { type FormEvent, useEffect, useState } from 'react'

import { API_BASE_URL } from '../config'

type FeedSourcesProps = {
  brandId: string
  onDataChanged: () => void
}

type FeedSource = {
  id: string
  brand_id: string
  name: string
  feed_url: string
  enabled: boolean
  interval_minutes: number
  max_articles_per_collection: number
  last_fetched_at: string | null
  last_success_at: string | null
  last_error: string | null
}

type CollectionResult = {
  discovered_count: number
  considered_count: number
  truncated_count: number
  imported_count: number
  skipped_count: number
  enqueued_count: number
}

async function getErrorMessage(response: Response, fallback: string) {
  const body = (await response.json()) as { detail?: unknown }
  return typeof body.detail === 'string' ? body.detail : fallback
}

export function FeedSources({
  brandId,
  onDataChanged,
}: FeedSourcesProps) {
  const [sources, setSources] = useState<FeedSource[]>([])
  const [sourceName, setSourceName] = useState('Brand News RSS')
  const [feedUrl, setFeedUrl] = useState('')
  const [intervalMinutes, setIntervalMinutes] = useState(15)
  const [maxArticles, setMaxArticles] = useState(5)
  const [sourceVersion, setSourceVersion] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [busySourceId, setBusySourceId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)

  useEffect(() => {
    let isCancelled = false

    async function loadSources() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/feed-sources?brand_id=${brandId}`,
        )

        if (!response.ok) {
          throw new Error(
            await getErrorMessage(response, 'RSS 数据源加载失败'),
          )
        }

        const data = (await response.json()) as FeedSource[]

        if (!isCancelled) {
          setSources(data)
          setError(null)
        }
      } catch (caughtError: unknown) {
        if (!isCancelled) {
          setError(
            caughtError instanceof Error
              ? caughtError.message
              : 'RSS 数据源加载失败',
          )
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadSources()

    return () => {
      isCancelled = true
    }
  }, [brandId, sourceVersion])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsCreating(true)
    setError(null)
    setFeedback(null)

    try {
      const response = await fetch(`${API_BASE_URL}/feed-sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_id: brandId,
          name: sourceName.trim(),
          feed_url: feedUrl.trim(),
          enabled: true,
          interval_minutes: intervalMinutes,
          max_articles_per_collection: maxArticles,
        }),
      })

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(response, 'RSS 数据源创建失败'),
        )
      }

      setFeedUrl('')
      setFeedback('RSS 数据源已保存，Collector 将按设定周期自动采集。')
      setSourceVersion((current) => current + 1)
    } catch (caughtError: unknown) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'RSS 数据源创建失败',
      )
    } finally {
      setIsCreating(false)
    }
  }

  async function handleCollect(source: FeedSource) {
    setBusySourceId(source.id)
    setError(null)
    setFeedback(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/feed-sources/${source.id}/collect`,
        { method: 'POST' },
      )

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(response, 'RSS 立即采集失败'),
        )
      }

      const result = (await response.json()) as CollectionResult
      setFeedback(
        `发现 ${result.discovered_count} 篇，按上限处理 ${result.considered_count} 篇，` +
          `忽略 ${result.truncated_count} 篇，新增 ${result.imported_count} 篇，` +
          `跳过 ${result.skipped_count} 篇，已提交 ${result.enqueued_count} 个分析任务。`,
      )
      setSourceVersion((current) => current + 1)
      onDataChanged()
    } catch (caughtError: unknown) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'RSS 立即采集失败',
      )
      setSourceVersion((current) => current + 1)
    } finally {
      setBusySourceId(null)
    }
  }

  async function handleToggle(source: FeedSource) {
    setBusySourceId(source.id)
    setError(null)
    setFeedback(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/feed-sources/${source.id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: !source.enabled }),
        },
      )

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(response, 'RSS 数据源状态修改失败'),
        )
      }

      setFeedback(source.enabled ? '已暂停自动采集。' : '已恢复自动采集。')
      setSourceVersion((current) => current + 1)
    } catch (caughtError: unknown) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'RSS 数据源状态修改失败',
      )
    } finally {
      setBusySourceId(null)
    }
  }

  return (
    <section className="panel feed-sources-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">AUTOMATED COLLECTION</p>
          <h2>RSS 自动采集</h2>
        </div>
        <span>{sources.length} 个数据源</span>
      </div>

      <form className="feed-source-form" onSubmit={handleCreate}>
        <label className="form-field">
          <span>数据源名称</span>
          <input
            value={sourceName}
            maxLength={100}
            required
            onChange={(event) => setSourceName(event.target.value)}
          />
        </label>

        <label className="form-field feed-source-url-field">
          <span>RSS Feed URL</span>
          <input
            value={feedUrl}
            type="url"
            placeholder="https://example.com/rss.xml"
            required
            onChange={(event) => setFeedUrl(event.target.value)}
          />
        </label>

        <label className="form-field">
          <span>采集间隔（分钟）</span>
          <input
            value={intervalMinutes}
            type="number"
            min={1}
            max={1440}
            required
            onChange={(event) =>
              setIntervalMinutes(Number(event.target.value))
            }
          />
        </label>

        <label className="form-field">
          <span>单次文章上限</span>
          <input
            value={maxArticles}
            type="number"
            min={1}
            max={50}
            required
            onChange={(event) => setMaxArticles(Number(event.target.value))}
          />
        </label>

        <button className="submit-button" type="submit" disabled={isCreating}>
          {isCreating ? '保存中……' : '添加数据源'}
        </button>
      </form>

      {(error || feedback) && (
        <div className="feed-source-feedback" role="status">
          {error && <p className="form-error">{error}</p>}
          {feedback && <p className="form-success">{feedback}</p>}
        </div>
      )}

      {isLoading ? (
        <p className="feed-source-state">正在加载 RSS 数据源……</p>
      ) : sources.length === 0 ? (
        <p className="feed-source-state">
          暂无 RSS 数据源。添加后可立即采集，也可等待 Collector 定时执行。
        </p>
      ) : (
        <ul className="feed-source-list">
          {sources.map((source) => (
            <li key={source.id}>
              <div className="feed-source-info">
                <div className="feed-source-title">
                  <h3>{source.name}</h3>
                  <span
                    className={
                      source.enabled
                        ? 'feed-source-badge feed-source-badge--enabled'
                        : 'feed-source-badge'
                    }
                  >
                    {source.enabled ? '自动采集中' : '已暂停'}
                  </span>
                </div>
                <p>{source.feed_url}</p>
                <div className="feed-source-meta">
                  <span>每 {source.interval_minutes} 分钟</span>
                  <span>
                    单次最多 {source.max_articles_per_collection} 篇
                  </span>
                  <span>
                    最近成功：
                    {source.last_success_at
                      ? new Date(source.last_success_at).toLocaleString('zh-CN')
                      : '尚未采集'}
                  </span>
                </div>
                {source.last_error && (
                  <p className="feed-source-error">
                    最近错误：{source.last_error}
                  </p>
                )}
              </div>

              <div className="feed-source-actions">
                <button
                  type="button"
                  className="analysis-button"
                  disabled={busySourceId !== null}
                  onClick={() => handleCollect(source)}
                >
                  {busySourceId === source.id ? '执行中……' : '立即采集'}
                </button>
                <button
                  type="button"
                  className="feed-source-toggle"
                  disabled={busySourceId !== null}
                  onClick={() => handleToggle(source)}
                >
                  {source.enabled ? '暂停' : '启用'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
