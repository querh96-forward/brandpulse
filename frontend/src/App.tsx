import { type ChangeEvent, useCallback, useEffect, useState } from 'react'

import './App.css'

import { ArticleForm } from './components/ArticleForm'
import { FeedSources } from './components/FeedSources'

import { RecentArticles } from './components/RecentArticles'

import { API_BASE_URL } from './config'

import {
  RiskTrendChart,
  type RiskTrendPoint,
} from './components/RiskTrendChart'

type MetricTone = 'default' | 'danger'

type Metric = {
  label: string
  value: string
  detail: string
  tone: MetricTone
}

type Brand = {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

type BrandRiskSummary = {
  brand_id: string
  total_articles: number
  analyzed_articles: number
  high_risk_articles: number
  average_risk_score: number
  positive_articles: number
  neutral_articles: number
  negative_articles: number
}

type HighRiskArticle = {
  article_id: string
  title: string
  source_name: string
  risk_level: 'high' | 'critical'
  risk_score: number
  risk_type: string
  summary: string
  published_at: string | null
  analyzed_at: string
}



function App() {
  const [dashboardVersion, setDashboardVersion] = useState(0)  
  const [brands, setBrands] = useState<Brand[]>([])
  const [selectedBrandId, setSelectedBrandId] = useState('')
  const [summary, setSummary] = useState<BrandRiskSummary | null>(null)
  const [riskArticles, setRiskArticles] = useState<HighRiskArticle[]>([])
  const [riskTrend, setRiskTrend] = useState<RiskTrendPoint[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedArticleId, setExpandedArticleId] = useState<string | null>(
    null,
  )

  useEffect(() => {
    async function loadBrands() {
      try {
        const response = await fetch(`${API_BASE_URL}/brands`)

        if (!response.ok) {
          throw new Error(
            `品牌列表请求失败，HTTP 状态码：${response.status}`,
          )
        }

        const data = (await response.json()) as Brand[]
        setBrands(data)

        if (data.length === 0) {
          setIsLoading(false)
          return
        }

        setSelectedBrandId(data[0].id)
      } catch (caughtError: unknown) {
        const message =
          caughtError instanceof Error ? caughtError.message : '未知请求错误'

        setError(message)
        setIsLoading(false)
      }
    }

    void loadBrands()
  }, [])

  useEffect(() => {
    if (!selectedBrandId) {
      return
    }
  
    async function loadDashboard() {
      try {
        const [
          summaryResponse,
          articlesResponse,
          trendResponse,
        ] = await Promise.all([
          fetch(
            `${API_BASE_URL}/brands/${selectedBrandId}/risk-summary`,
          ),
          fetch(
            `${API_BASE_URL}/brands/${selectedBrandId}/high-risk-articles?offset=0&limit=10`,
          ),
          fetch(
            `${API_BASE_URL}/brands/${selectedBrandId}/risk-trend?days=30`,
          ),
        ])
  
        if (!summaryResponse.ok) {
          throw new Error(
            `概览请求失败，HTTP 状态码：${summaryResponse.status}`,
          )
        }
  
        if (!articlesResponse.ok) {
          throw new Error(
            `文章请求失败，HTTP 状态码：${articlesResponse.status}`,
          )
        }
  
        if (!trendResponse.ok) {
          throw new Error(
            `趋势请求失败，HTTP 状态码：${trendResponse.status}`,
          )
        }
  
        const [
          summaryData,
          articlesData,
          trendData,
        ] = await Promise.all([
          summaryResponse.json() as Promise<BrandRiskSummary>,
          articlesResponse.json() as Promise<HighRiskArticle[]>,
          trendResponse.json() as Promise<RiskTrendPoint[]>,
        ])
  
        setSummary(summaryData)
        setRiskArticles(articlesData)
        setRiskTrend(trendData)
      } catch (caughtError: unknown) {
        const message =
          caughtError instanceof Error ? caughtError.message : '未知请求错误'
  
        setError(message)
      } finally {
        setIsLoading(false)
      }
    }
  
    void loadDashboard()
  }, [selectedBrandId, dashboardVersion])

  const refreshDashboard = useCallback(() => {
    setIsLoading(true)
    setError(null)
    setDashboardVersion((currentVersion) => currentVersion + 1)
  }, [])

  function handleBrandChange(event: ChangeEvent<HTMLSelectElement>) {
    setSelectedBrandId(event.target.value)
    setSummary(null)
    setRiskArticles([])
    setRiskTrend([])
    setError(null)
    setIsLoading(true)
    setExpandedArticleId(null)
  }

  function toggleArticle(articleId: string) {
    setExpandedArticleId((currentId) =>
      currentId === articleId ? null : articleId,
    )
  }

  const metrics: Metric[] = [
    {
      label: '已分析文章',
      value: summary ? String(summary.analyzed_articles) : '--',
      detail: summary
        ? `共采集 ${summary.total_articles} 篇`
        : '等待后端数据',
      tone: 'default',
    },
    {
      label: '高风险文章',
      value: summary ? String(summary.high_risk_articles) : '--',
      detail: '需要重点关注',
      tone: 'danger',
    },
    {
      label: '平均风险分',
      value: summary ? summary.average_risk_score.toFixed(2) : '--',
      detail: '当前品牌风险水平',
      tone: 'danger',
    },
  ]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI BRAND INTELLIGENCE</p>
          <h1>BrandPulse</h1>
          <p className="subtitle">品牌舆情风险监控台</p>
        </div>

        <div className="header-actions">
          <label className="brand-picker">
            <span>当前品牌</span>
            <select
              value={selectedBrandId}
              onChange={handleBrandChange}
              disabled={brands.length === 0}
            >
              <option value="">请选择品牌</option>
              {brands.map((brand) => (
                <option value={brand.id} key={brand.id}>
                  {brand.name}
                </option>
              ))}
            </select>
          </label>

          <div
            className={`system-status${
              error ? ' system-status--error' : ''
            }`}
          >
            <span className="status-dot" />
            {isLoading
              ? '正在读取数据'
              : error
                ? '后端连接失败'
                : selectedBrandId
                  ? '系统运行中'
                  : '暂无品牌'}
          </div>
        </div>
      </header>

      {error && <p className="error-message">加载失败：{error}</p>}

      <main>
        <section className="metric-grid" aria-label="风险概览">
          {metrics.map((metric) => (
            <article
              className={`metric-card ${
                metric.tone === 'danger' ? 'metric-card--danger' : ''
              }`}
              key={metric.label}
            >
              <p>{metric.label}</p>
              <strong>{metric.value}</strong>
              <span>{metric.detail}</span>
            </article>
          ))}
        </section>

        {selectedBrandId && (
          <FeedSources
            key={`feeds-${selectedBrandId}`}
            brandId={selectedBrandId}
            onDataChanged={refreshDashboard}
          />
        )}

        <ArticleForm
          key={selectedBrandId}
          brandId={selectedBrandId}
          onDataChanged={refreshDashboard}
        />

        {selectedBrandId && (
          <RecentArticles
            key={selectedBrandId}
            brandId={selectedBrandId}
            refreshVersion={dashboardVersion}
            onDataChanged={refreshDashboard}
          />
        )}

        <section className="panel trend-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">RISK TREND</p>
              <h2>平均风险趋势</h2>
            </div>
            <span>近 30 天</span>
          </div>

          <RiskTrendChart
            data={riskTrend}
            isLoading={isLoading}
          />
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">HIGH RISK ALERTS</p>
              <h2>高风险舆情</h2>
            </div>
            <span>{riskArticles.length} 条记录</span>
          </div>

          <ul className="risk-list">
            {isLoading ? (
              <li className="empty-state">正在加载舆情数据……</li>
            ) : riskArticles.length === 0 ? (
              <li className="empty-state">当前品牌暂无高风险舆情</li>
            ) : (
              riskArticles.map((article) => {
                const isExpanded = expandedArticleId === article.article_id
              
                return (
                  <li key={article.article_id}>
                    <button
                      type="button"
                      className="risk-row"
                      aria-expanded={isExpanded}
                      onClick={() => toggleArticle(article.article_id)}
                    >
                      <div className="risk-content">
                        <h3>{article.title}</h3>
                        <p>
                          {article.source_name} · {article.risk_type}
                        </p>
                      </div>
              
                      <div className="risk-actions">
                        <div className="risk-score">
                          <span>{article.risk_level.toUpperCase()}</span>
                          <strong>{article.risk_score.toFixed(2)}</strong>
                        </div>
              
                        <span className="expand-label">
                          {isExpanded ? '收起' : '查看分析'}
                        </span>
                      </div>
                    </button>
              
                    {isExpanded && (
                      <div className="risk-detail">
                        <p className="detail-label">AI 风险摘要</p>
                        <p className="detail-summary">{article.summary}</p>
              
                        <div className="detail-meta">
                          <span>风险类型：{article.risk_type}</span>
                          <span>
                            分析时间：
                            {new Date(article.analyzed_at).toLocaleString('zh-CN')}
                          </span>
                        </div>
                      </div>
                    )}
                  </li>
                )
              })
            )}
          </ul>
        </section>
      </main>
    </div>
  )
}

export default App
