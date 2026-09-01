import { useEffect, useState } from 'react'

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
  status: 'pending' | 'completed'
  result: AnalysisResult | null
}

type ArticleWithStatus = Article & {
  analysisStatus: AnalysisStatus['status']
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

  useEffect(() => {
    if (!brandId) {
      return
    }

    let isCancelled = false

    async function loadArticles() {
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
              analysisResult: statusData.result,
            }
          }),
        )

        if (!isCancelled) {
          setArticles(articlesWithStatus)
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
        }
      }
    }

    void loadArticles()

    return () => {
      isCancelled = true
    }
  }, [brandId, refreshVersion])

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
        <span>{articles.length} 篇</span>
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
                  </div>

                  <div className="recent-article-actions">
                    <span
                      className={`article-analysis-status article-analysis-status--${article.analysisStatus}`}
                    >
                      {article.analysisStatus === 'completed'
                        ? '已分析'
                        : '尚无结果'}
                    </span>

                    {article.analysisStatus === 'pending' ? (
                      <button
                        type="button"
                        className="recent-analyze-button"
                        disabled={analyzingArticleId !== null}
                        onClick={() => handleAnalyze(article.id)}
                      >
                        {analyzingArticleId === article.id
                          ? '分析中……'
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
