import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
  } from 'recharts'
  
  export type RiskTrendPoint = {
    day: string
    analyzed_articles: number
    high_risk_articles: number
    average_risk_score: number
  }
  
  type RiskTrendChartProps = {
    data: RiskTrendPoint[]
    isLoading: boolean
  }
  
  export function RiskTrendChart({
    data,
    isLoading,
  }: RiskTrendChartProps) {
    if (isLoading) {
      return <div className="chart-state">正在加载趋势数据……</div>
    }
  
    if (data.length === 0) {
      return <div className="chart-state">当前品牌暂无趋势数据</div>
    }
  
    return (
      <div className="trend-chart">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={data}
            margin={{
              top: 20,
              right: 24,
              bottom: 5,
              left: 0,
            }}
          >
            <CartesianGrid stroke="#1c2c42" strokeDasharray="4 4" />
  
            <XAxis
              dataKey="day"
              stroke="#71839c"
              tickFormatter={(day: string) => day.slice(5)}
            />
  
            <YAxis
              domain={[0, 1]}
              stroke="#71839c"
              tickCount={6}
              width={42}
            />
  
            <Tooltip
              contentStyle={{
                border: '1px solid #263b55',
                borderRadius: '10px',
                background: '#0d1a2c',
              }}
              labelStyle={{ color: '#e8edf7' }}
            />
  
            <Line
              type="monotone"
              dataKey="average_risk_score"
              name="平均风险分"
              stroke="#ff7185"
              strokeWidth={3}
              dot={{
                r: 5,
                fill: '#07111f',
                strokeWidth: 3,
              }}
              activeDot={{ r: 7 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }