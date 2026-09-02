import { useEffect, useRef, useState } from 'react'

import { API_BASE_URL } from '../config'

type RecentArticlesProps = {
  brandId: string
  refreshVersion: number
  onDataChanged: () => void
}

type AnalysisJobStatus = 'queued' | 'processing' | 'completed' | 'failed'

type CreatedAnalysisJob = {
  job_id: string
}

type AnalysisJob = {
  status: AnalysisJobStatus
  last_error: string | null
}

type Article = {
  id: string
  title: string
  source_name: string
  created_at: string
}

type Sentiment = 'positive' | 'neutral' | 'negative'
type RiskLevel = 'low' | 'medium' | 'high'

type AnalysisResult = {
  sentiment: Sentiment
  sentiment_score: number
  risk_level: RiskLevel
  risk_score: number
  risk_type: string
  summary: string
  suggestion: string | null
  model_name: string
  prompt_version: string
}

type AnalysisStatus = {
  article_id: string
  status: 'not_submitted' | AnalysisJobStatus
  job_id: string | null
  attempts: number
  last_error: string | null
  result: AnalysisResult | null
}

type ArticleWithStatus = Article & {
  analysisStatus: AnalysisStatus['status']
  analysisAttempts: number
  analysisError: string | null
  analysisResult: AnalysisResult | null
}

const SENTIMENT_LABELS: Record<Sentiment, string> = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
}

const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
}

const POLL_INTERVAL_MS = 2000
const MAX_POLLS = 180
const ACTIVE_REFRESH_INTERVAL_MS = 5000
const IDLE_REFRESH_INTERVAL_MS = 30000

const ANALYSIS_STATUS_LABELS: Record<AnalysisStatus['status'], string> = {
  not_submitted: '未提交',
  queued: '排队中',
  processing: '分析中',
  completed: '已分析',
  failed: '分析失败',
}

function wait(milliseconds: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, milliseconds)
  })
}

export function RecentArticles({
  brandId,
  refreshVersion,
  onDataChanged,
}: RecentArticlesProps) {
  const [articles, setArticles] = useState<ArticleWithStatus[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analyzingArticleId, setAnalyzingArticleId] = useState<
    string | null
  >(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [expandedArticleId, setExpandedArticleId] = useState<
    string | null
  >(null)
  const [isAutoRefreshing, setIsAutoRefreshing] = useState(false)
  const previousStatusesRef = useRef<Map<string, AnalysisStatus['status']> | null>(
    null,
  )

  useEffect(() => {
    if (!brandId) {
      return
    }

    let isCancelled = false
    let refreshTimer: ReturnType<typeof setTimeout> | undefined

    async function loadArticles() {
      let nextRefreshInterval = IDLE_REFRESH_INTERVAL_MS

      try {
        const response = await fetch(
          `${API_BASE_URL}/articles?brand_id=${brandId}&offset=0&limit=10`,
        )

        if (!response.ok) {
          throw new Error(
            `文章列表请求失败，HTTP 状态码：${response.status}`,
          )
        }

        const articleData = (await response.json()) as Article[]

        const articlesWithStatus = await Promise.all(
          articleData.map(async (article) => {
            const statusResponse = await fetch(
              `${API_BASE_URL}/articles/${article.id}/analysis/status`,
            )

            if (!statusResponse.ok) {
              throw new Error(
                `分析状态请求失败，HTTP 状态码：${statusResponse.status}`,
              )
            }

            const statusData =
              (await statusResponse.json()) as AnalysisStatus

            return {
              ...article,
              analysisStatus: statusData.status,
              analysisAttempts: statusData.attempts,
              analysisError: statusData.last_error,
              analysisResult: statusData.result,
            }
          }),
        )

        if (!isCancelled) {
          const hasActiveJobs = articlesWithStatus.some(
            (article) =>
              article.analysisStatus === 'queued' ||
              article.analysisStatus === 'processing',
          )
          const currentStatuses = new Map(
            articlesWithStatus.map((article) => [
              article.id,
              article.analysisStatus,
            ]),
          )
          const previousStatuses = previousStatusesRef.current
          const hasNewCompletedAnalysis = articlesWithStatus.some(
            (article) =>
              article.analysisStatus === 'completed' &&
              previousStatuses?.get(article.id) !== 'completed',
          )

          setArticles(articlesWithStatus)
          setError(null)
          setIsAutoRefreshing(hasActiveJobs)
          previousStatusesRef.current = currentStatuses
          nextRefreshInterval = hasActiveJobs
            ? ACTIVE_REFRESH_INTERVAL_MS
            : IDLE_REFRESH_INTERVAL_MS

          if (previousStatuses !== null && hasNewCompletedAnalysis) {
            onDataChanged()
          }
        }
      } catch (caughtError: unknown) {
        if (!isCancelled) {
          const message =
            caughtError instanceof Error
              ? caughtError.message
              : '未知请求错误'

          setError(message)
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
          refreshTimer = setTimeout(
            () => void loadArticles(),
            nextRefreshInterval,
          )
        }
      }
    }

    void loadArticles()

    return () => {
      isCancelled = true
      if (refreshTimer !== undefined) {
        clearTimeout(refreshTimer)
      }
    }
  }, [brandId, refreshVersion, onDataChanged])

  async function pollAnalysisJob(jobId: string) {
    for (let pollCount = 0; pollCount < MAX_POLLS; pollCount += 1) {
      const response = await fetch(
        `${API_BASE_URL}/analysis-jobs/${jobId}`,
      )

      if (!response.ok) {
        throw new Error(
          `任务状态请求失败，HTTP 状态码：${response.status}`,
        )
      }

      const job = (await response.json()) as AnalysisJob

      if (job.status === 'completed') {
        return
      }

      if (job.status === 'failed') {
        throw new Error(job.last_error ?? 'AI 分析任务失败')
      }

      await wait(POLL_INTERVAL_MS)
    }

    throw new Error('等待 AI 分析超时，请稍后重试')
  }

  async function handleAnalyze(articleId: string) {
    setAnalyzingArticleId(articleId)
    setAnalysisError(null)

    let completed = false

    try {
      const response = await fetch(
        `${API_BASE_URL}/articles/${articleId}/analyze/async`,
        { method: 'POST' },
      )

      if (!response.ok) {
        throw new Error(
          `提交分析失败，HTTP 状态码：${response.status}`,
        )
      }

      const job = (await response.json()) as CreatedAnalysisJob

      setArticles((currentArticles) =>
        currentArticles.map((article) =>
          article.id === articleId
            ? { ...article, analysisStatus: 'queued' }
            : article,
        ),
      )

      await pollAnalysisJob(job.job_id)

      setArticles((currentArticles) =>
        currentArticles.map((article) =>
          article.id === articleId
            ? { ...article, analysisStatus: 'completed' }
            : article,
        ),
      )
      completed = true
    } catch (caughtError: unknown) {
      const message =
        caughtError instanceof Error ? caughtError.message : '未知分析错误'

      setAnalysisError(message)
    } finally {
      setAnalyzingArticleId(null)
    }

    if (completed) {
      onDataChanged()
    }
  }

  function toggleResult(articleId: string) {
    setExpandedArticleId((currentId) =>
      currentId === articleId ? null : articleId,
    )
  }

  return (
    <section className="panel recent-articles-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">RECENT ARTICLES</p>
          <h2>最近采集文章</h2>
        </div>
        <span>
          {articles.length} 篇 ·{' '}
          {isAutoRefreshing ? '5 秒刷新' : '30 秒巡检'}
        </span>
      </div>

      {analysisError && (
        <p className="recent-articles-error" role="alert">
          分析失败：{analysisError}
        </p>
      )}

      {error ? (
        <p className="recent-articles-state">加载失败：{error}</p>
      ) : isLoading ? (
        <p className="recent-articles-state">正在加载文章……</p>
      ) : articles.length === 0 ? (
        <p className="recent-articles-state">当前品牌暂无文章</p>
      ) : (
        <ul className="recent-article-list">
          {articles.map((article) => {
            const isExpanded = expandedArticleId === article.id

            return (
              <li key={article.id}>
                <div className="recent-article-row">
                  <div>
                    <h3>{article.title}</h3>
                    <p>
                      {article.source_name} ·{' '}
                      {new Date(article.created_at).toLocaleString('zh-CN')}
                    </p>
                    {article.analysisStatus === 'failed' && (
                      <p className="recent-analysis-failure">
                        第 {article.analysisAttempts} 次尝试失败：
                        {article.analysisError ?? '未记录错误详情'}
                      </p>
                    )}
                  </div>

                  <div className="recent-article-actions">
                    <span
                      className={`article-analysis-status article-analysis-status--${article.analysisStatus}`}
                    >
                      {ANALYSIS_STATUS_LABELS[article.analysisStatus]}
                    </span>

                    {article.analysisStatus === 'not_submitted' ||
                    article.analysisStatus === 'failed' ? (
                      <button
                        type="button"
                        className="recent-analyze-button"
                        disabled={analyzingArticleId !== null}
                        onClick={() => handleAnalyze(article.id)}
                      >
                        {analyzingArticleId === article.id
                          ? '分析中……'
                          : article.analysisStatus === 'failed'
                            ? '重新分析'
                            : '提交分析'}
                      </button>
                    ) : article.analysisResult ? (
                      <button
                        type="button"
                        className="recent-result-button"
                        aria-expanded={isExpanded}
                        onClick={() => toggleResult(article.id)}
                      >
                        {isExpanded ? '收起结果' : '查看结果'}
                      </button>
                    ) : null}
                  </div>
                </div>

                {isExpanded && article.analysisResult && (
                  <div className="recent-article-detail">
                    <div className="recent-result-meta">
                      <span>
                        情感：
                        {SENTIMENT_LABELS[article.analysisResult.sentiment]}
                        （
                        {article.analysisResult.sentiment_score.toFixed(2)}）
                      </span>
                      <span>
                        风险：
                        {
                          RISK_LEVEL_LABELS[
                            article.analysisResult.risk_level
                          ]
                        }
                        （{article.analysisResult.risk_score.toFixed(2)}）
                      </span>
                      <span>
                        类型：{article.analysisResult.risk_type}
                      </span>
                    </div>

                    <p className="detail-label">AI 事件摘要</p>
                    <p className="recent-result-text">
                      {article.analysisResult.summary}
                    </p>

                    {article.analysisResult.suggestion && (
                      <>
                        <p className="detail-label">处置建议</p>
                        <p className="recent-result-text">
                          {article.analysisResult.suggestion}
                        </p>
                      </>
                    )}

                    <p className="recent-result-model">
                      模型：{article.analysisResult.model_name} · Prompt：
                      {article.analysisResult.prompt_version}
                    </p>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
