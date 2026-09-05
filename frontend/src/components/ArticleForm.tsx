import { type FormEvent, useState } from 'react'

import { API_BASE_URL } from '../config'

type ArticleFormProps = {
  brandId: string
  onDataChanged: () => void
}

type CreatedArticle = {
  id: string
}

type JobStatus = 'idle' | 'queued' | 'processing' | 'completed' | 'failed'

type CreatedAnalysisJob = {
  job_id: string
  article_id: string
  status: 'queued' | 'processing'
  queue_length: number | null
  reused: boolean
}

type Sentiment = 'positive' | 'neutral' | 'negative'
type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

type KnowledgeCitation = {
  rank: number
  chunk_id: string
  source_name: string
  section_title: string | null
  similarity: number
}

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
  knowledge_used: boolean
  knowledge_citations: KnowledgeCitation[]
  retrieval_model_name: string | null
  evidence_model_name: string | null
  evidence_reason: string | null
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
  critical: '严重风险',
}

type AnalysisJob = {
  job_id: string
  article_id: string
  status: Exclude<JobStatus, 'idle'>
  attempts: number
  last_error: string | null
  created_at: string
  updated_at: string
}

const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  idle: '尚未提交',
  queued: '等待处理',
  processing: 'AI 分析中',
  completed: '分析完成',
  failed: '分析失败',
}

const POLL_INTERVAL_MS = 2000
const MAX_POLLS = 180

function wait(milliseconds: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, milliseconds)
  })
}

export function ArticleForm({
  brandId,
  onDataChanged,
}: ArticleFormProps) {
  const [sourceName, setSourceName] = useState('Web Manual Input')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [articleError, setArticleError] = useState<string | null>(null)
  const [createdArticleId, setCreatedArticleId] = useState<string | null>(
    null,
  )

  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus>('idle')
  const [jobAttempts, setJobAttempts] = useState(0)
  const [queueLength, setQueueLength] = useState<number | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] =
    useState<AnalysisResult | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!brandId) {
      setArticleError('请先选择品牌')
      return
    }

    setIsSubmitting(true)
    setArticleError(null)
    setCreatedArticleId(null)
    setJobId(null)
    setJobStatus('idle')
    setJobAttempts(0)
    setQueueLength(null)
    setAnalysisError(null)
    setAnalysisResult(null)

    try {
      const response = await fetch(`${API_BASE_URL}/articles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_id: brandId,
          source_type: 'manual',
          source_name: sourceName.trim(),
          title: title.trim(),
          content: content.trim(),
          url: null,
          published_at: null,
        }),
      })

      if (!response.ok) {
        const errorBody = (await response.json()) as {
          detail?: unknown
        }

        const message =
          typeof errorBody.detail === 'string'
            ? errorBody.detail
            : `创建失败，HTTP 状态码：${response.status}`

        throw new Error(message)
      }

      const article = (await response.json()) as CreatedArticle

      setCreatedArticleId(article.id)
      setTitle('')
      setContent('')
      onDataChanged()
    } catch (caughtError: unknown) {
      const message =
        caughtError instanceof Error ? caughtError.message : '未知请求错误'

      setArticleError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function pollAnalysisJob(nextJobId: string) {
    for (let pollCount = 0; pollCount < MAX_POLLS; pollCount += 1) {
      const response = await fetch(
        `${API_BASE_URL}/analysis-jobs/${nextJobId}`,
      )

      if (!response.ok) {
        throw new Error(
          `查询任务失败，HTTP 状态码：${response.status}`,
        )
      }

      const job = (await response.json()) as AnalysisJob

      setJobStatus(job.status)
      setJobAttempts(job.attempts)

      if (job.status === 'completed') {
        return
      }

      if (job.status === 'failed') {
        throw new Error(job.last_error ?? 'AI 分析任务失败')
      }

      await wait(POLL_INTERVAL_MS)
    }

    throw new Error('等待 AI 分析超时，请稍后查询任务状态')
  }

  async function fetchAnalysisResult(
    articleId: string,
  ): Promise<AnalysisResult> {
    const response = await fetch(
      `${API_BASE_URL}/articles/${articleId}/analysis`,
    )

    if (!response.ok) {
      throw new Error(
        `获取分析结果失败，HTTP 状态码：${response.status}`,
      )
    }

    return (await response.json()) as AnalysisResult
  }

  async function handleAnalyze() {
    if (!createdArticleId) {
      return
    }

    setIsAnalyzing(true)
    setAnalysisError(null)
    setJobId(null)
    setJobStatus('idle')
    setJobAttempts(0)
    setQueueLength(null)
    setAnalysisResult(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/articles/${createdArticleId}/analyze/async`,
        {
          method: 'POST',
        },
      )

      if (!response.ok) {
        throw new Error(
          `提交分析失败，HTTP 状态码：${response.status}`,
        )
      }

      const createdJob = (await response.json()) as CreatedAnalysisJob

      setJobId(createdJob.job_id)
      setJobStatus(createdJob.status)
      setQueueLength(createdJob.queue_length)

      await pollAnalysisJob(createdJob.job_id)

      const result = await fetchAnalysisResult(createdArticleId)
      setAnalysisResult(result)
      onDataChanged()
    } catch (caughtError: unknown) {
      const message =
        caughtError instanceof Error ? caughtError.message : '未知分析错误'

      setAnalysisError(message)
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <section className="panel article-form-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">MANUAL COLLECTION</p>
          <h2>录入舆情文章</h2>
        </div>
        <span>PostgreSQL + Redis + AI Worker</span>
      </div>

      <form className="article-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="form-field">
            <span>来源名称</span>
            <input
              type="text"
              value={sourceName}
              maxLength={100}
              required
              onChange={(event) => setSourceName(event.target.value)}
            />
          </label>

          <label className="form-field">
            <span>文章标题</span>
            <input
              type="text"
              value={title}
              maxLength={500}
              placeholder="例如：用户反馈水下设备密封失效"
              required
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>

          <label className="form-field form-field--wide">
            <span>文章正文</span>
            <textarea
              value={content}
              rows={6}
              placeholder="输入需要进行 AI 风险分析的完整正文"
              required
              onChange={(event) => setContent(event.target.value)}
            />
          </label>
        </div>

        <div className="form-footer">
          <div className="form-feedback">
            {articleError && (
              <p className="form-error" role="alert">
                {articleError}
              </p>
            )}

            {createdArticleId && (
              <p className="form-success">
                文章创建成功，ID：{createdArticleId}
              </p>
            )}
          </div>

          <button
            type="submit"
            className="submit-button"
            disabled={!brandId || isSubmitting || isAnalyzing}
          >
            {isSubmitting ? '正在保存……' : '保存文章'}
          </button>
        </div>
      </form>

      {createdArticleId && (
        <div className="analysis-control">
          <div className="analysis-control-heading">
            <div>
              <p className="detail-label">异步 AI 分析</p>
              <p className="analysis-description">
                将文章任务写入 Redis，由独立 Worker 调用大模型。
              </p>
            </div>

            <button
              type="button"
              className="analysis-button"
              disabled={isAnalyzing || jobStatus === 'completed'}
              onClick={handleAnalyze}
            >
              {isAnalyzing
                ? '正在分析……'
                : jobStatus === 'completed'
                  ? '分析已完成'
                  : jobStatus === 'failed'
                    ? '重新提交分析'
                    : '提交 AI 分析'}
            </button>
          </div>

          {jobStatus !== 'idle' && (
            <div className="job-progress">
              <span
                className={`job-status job-status--${jobStatus}`}
              >
                {JOB_STATUS_LABELS[jobStatus]}
              </span>

              <span>执行次数：{jobAttempts}</span>

              {queueLength !== null && (
                <span>提交时队列长度：{queueLength}</span>
              )}

              {jobId && <span className="job-id">任务 ID：{jobId}</span>}
            </div>
          )}

          {analysisError && (
            <p className="form-error analysis-error" role="alert">
              {analysisError}
            </p>
          )}

          {analysisResult && (
            <div className="analysis-result">
              <div className="analysis-result-heading">
                <div>
                  <p className="detail-label">AI 分析结果</p>
                  <h3>{analysisResult.risk_type}</h3>
                </div>

                <span
                  className={`analysis-result-risk analysis-result-risk--${analysisResult.risk_level}`}
                >
                  {RISK_LEVEL_LABELS[analysisResult.risk_level]}
                </span>
              </div>

              <div className="analysis-result-metrics">
                <div>
                  <span>舆情情感</span>
                  <strong>
                    {SENTIMENT_LABELS[analysisResult.sentiment]}
                  </strong>
                </div>

                <div>
                  <span>情感分数</span>
                  <strong>
                    {analysisResult.sentiment_score.toFixed(2)}
                  </strong>
                </div>

                <div>
                  <span>风险分数</span>
                  <strong>{analysisResult.risk_score.toFixed(2)}</strong>
                </div>
              </div>

              <div className="analysis-result-section">
                <p className="detail-label">事件摘要</p>
                <p>{analysisResult.summary}</p>
              </div>

              {analysisResult.suggestion && (
                <div className="analysis-result-section">
                  <p className="detail-label">处置建议</p>
                  <p>{analysisResult.suggestion}</p>
                </div>
              )}

              <div
                className={`rag-trace ${
                  analysisResult.knowledge_used
                    ? 'rag-trace--used'
                    : 'rag-trace--unused'
                }`}
              >
                <div className="rag-trace-heading">
                  <p className="detail-label">RAG 知识依据</p>
                  <strong>
                    {analysisResult.knowledge_used
                      ? '已使用品牌内部知识'
                      : '未使用品牌内部知识'}
                  </strong>
                </div>

                {analysisResult.evidence_reason && (
                  <p>{analysisResult.evidence_reason}</p>
                )}

                {analysisResult.knowledge_citations.length > 0 && (
                  <ul className="rag-citation-list">
                    {analysisResult.knowledge_citations.map((citation) => (
                      <li key={citation.chunk_id}>
                        <span>
                          {citation.source_name} ·{' '}
                          {citation.section_title ?? '未命名章节'}
                        </span>
                        <strong>
                          相似度 {citation.similarity.toFixed(4)}
                        </strong>
                      </li>
                    ))}
                  </ul>
                )}

                {analysisResult.knowledge_used && (
                  <p className="rag-trace-models">
                    检索：{analysisResult.retrieval_model_name} · 审核：
                    {analysisResult.evidence_model_name}
                  </p>
                )}
              </div>

              <p className="analysis-result-model">
                模型：{analysisResult.model_name} · Prompt：
                {analysisResult.prompt_version}
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
