"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ScrollArea } from "@/components/ui/scroll-area"
import { getSignalAnalysis } from "@/lib/trader-agent"

interface HighProbabilitySetup {
  icon: string
  setupType: string
  confidenceLevel: string
  direction: string
  probability: number
  entryCriteria: string
  target: string
  session: string
  riskManagement: string
  confluenceFactors: string[]
}

interface CandlestickPatterns {
  ltf: Array<{
    pattern: string
    price: number
    strength: string
    direction: string
  }>
  htf: Array<{
    pattern: string
    price: number
    strength: string
    direction: string
  }>
  daily: Array<{
    pattern: string
    price: number
    strength: string
    direction: string
  }>
}

interface CandlestickDisplay {
  ltf: string[]
  htf: string[]
  daily: string[]
}

interface MarketStructure {
  ltf: {
    value_area_high: number | null
    value_area_low: number | null
    point_of_control: number | null
    swing_highs: number[]
    swing_lows: number[]
  }
  htf: {
    value_area_high: number | null
    value_area_low: number | null
    point_of_control: number | null
    swing_highs: number[]
    swing_lows: number[]
  }
  daily: {
    value_area_high: number | null
    value_area_low: number | null
    point_of_control: number | null
    swing_highs: number[]
    swing_lows: number[]
  }
}

interface OrderFlow {
  ltf: {
    buying_pressure: string
    selling_pressure: string
    cvd_trend: string
    cumulative_volume_delta: number
  }
  htf: {
    buying_pressure: string
    selling_pressure: string
    cvd_trend: string
    cumulative_volume_delta: number
  }
  daily: {
    buying_pressure: string
    selling_pressure: string
    cvd_trend: string
    cumulative_volume_delta: number
  }
}

interface FabioAnalysis {
  session: string
  market_state: string
  buying_pressure: string
  selling_pressure: string
  cvd_trend: string
}

interface CandlestickPattern {
  pattern_type: string
  candle_index: number
  timeframe: string
  strength: string
  price: number
  description: string
}

interface TradingSignal {
  formatted: boolean
  token: string
  currentPrice: number
  action: "BUY" | "SELL" | "HOLD"
  entryPrice: number
  stopLoss: number
  takeProfit: number
  convictionScore: number
  riskRewardRatio: number
  reasoning: string
  strategy?: string
  timestamp: string
  highProbabilitySetups: HighProbabilitySetup[]
  candlestickPatterns?: CandlestickPatterns
  candlestickDisplay?: CandlestickDisplay
  marketStructure?: MarketStructure
  orderFlow?: OrderFlow
  fabioAnalysis?: FabioAnalysis
  tradingOpportunities?: Array<{
    time: string
    status: string
    details: string[]
  }>
  gemini_analysis?: string
  raw: TradingSignal
}

export default function Home() {
  const [token, setToken] = useState("SOL")
  const [chain, setChain] = useState("solana")
  const [loading, setLoading] = useState(false)
  const [dataComparison, setDataComparison] = useState<any | null>(null)
  const [showingComparison, setShowingComparison] = useState(false)
  const [result, setResult] = useState<any | null>(null)
  const [error, setError] = useState("")

  const handleAnalyze = async () => {
    setLoading(true)
    setError("")
    setResult(null)

    try {
      console.log(`🚀 Starting Trading Agent for ${token} on ${chain}...`)
      const data = await getSignalAnalysis(token, chain)
      setResult(data)
      console.log("✅ Analysis complete - check the console above for detailed output")
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      console.error("❌ Analysis failed:", err)
    } finally {
      setLoading(false)
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'bg-green-500'
      case 'SELL': return 'bg-red-500'
      case 'HOLD': return 'bg-yellow-500'
      default: return 'bg-gray-500'
    }
  }

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'BUY': return '📈'
      case 'SELL': return '📉'
      case 'HOLD': return '⏸️'
      default: return '⚪'
    }
  }

  const getRiskRewardColor = (ratio: number) => {
    if (ratio >= 2) return 'text-green-400'
    if (ratio >= 1.5) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return 'bg-green-500'
    if (score >= 60) return 'bg-yellow-500'
    if (score >= 40) return 'bg-orange-500'
    return 'bg-red-50'
  }

  const getConfidenceLevelColor = (level: string) => {
    if (level.includes('HIGH')) return 'bg-green-500 text-white'
    if (level.includes('MEDIUM')) return 'bg-yellow-500 text-black'
    if (level.includes('LOW')) return 'bg-red-500 text-white'
    return 'bg-gray-500 text-white'
  }

  const getDetailedAnalysis = () => {
    if (!result) return ''

    let analysis = result.reasoning

    // Add strategy info if available
    if (result.strategy && result.strategy !== 'Neutral') {
      analysis += `\n\n🎯 Strategy: ${result.strategy}`
    }

    // Add candlestick patterns if available
    if (result.candlestickDisplay) {
      const patterns = Object.entries(result.candlestickDisplay)
        .filter(([timeframe, patternList]) => Array.isArray(patternList) && patternList.length > 0)
        .map(([timeframe, patternList]) =>
          `${timeframe.toUpperCase()}: ${(patternList as string[]).join(', ')}`
        )

      if (patterns.length > 0) {
        analysis += `\n\n📊 Recent Candlestick Patterns:\n${patterns.join('\n')}`
      }
    }

    // Add market structure info if available
    if (result.marketStructure?.htf) {
      const htf = result.marketStructure.htf
      if (htf.point_of_control) {
        analysis += `\n\n📈 Market Structure:\n• HTF Point of Control: $${htf.point_of_control.toFixed(2)}`
      }
      if (htf.value_area_high && htf.value_area_low) {
        analysis += `\n• HTF Value Area: $${htf.value_area_low.toFixed(2)} - $${htf.value_area_high.toFixed(2)}`
      }
    }

    // Add order flow info if available
    if (result.orderFlow?.htf) {
      const of = result.orderFlow.htf
      analysis += `\n\n💹 Order Flow Analysis:\n• Buying Pressure: ${of.buying_pressure}\n• Selling Pressure: ${of.selling_pressure}\n• CVD Trend: ${of.cvd_trend}`
    }

    // Add session info if available
    if (result.fabioAnalysis?.session) {
      analysis += `\n\n🕐 Trading Session: ${result.fabioAnalysis.session} (${result.fabioAnalysis.market_state})`
    }

    // Add Gemini-enhanced analysis if available
    if (result.gemini_analysis) {
      analysis += `\n\n🤖 Gemini Analysis:\n${result.gemini_analysis}`
    }

    return analysis
  }

  // Function to get data comparison (what's calculated vs what's sent to Gemini)
  const handleDataComparison = async () => {
    try {
      const response = await fetch('/api/data-comparison', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          chain
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}`);
      }

      const data = await response.json();
      setDataComparison(data);
      setShowingComparison(true);
    } catch (error) {
      console.error('Error fetching data comparison:', error);
      setError(`Failed to get data comparison: ${(error as Error).message}`);
    }
  };

  // Function to enhance analysis with Gemini
  const enhanceWithGemini = async (currentAnalysis: string) => {
    if (!result) return;

    try {
      // Create a prompt for Gemini to enhance the current analysis
      const geminiPrompt = `
        Analyze the following trading data and provide additional insights:

        Current Analysis: ${currentAnalysis}

        Token: ${result.token}
        Current Price: $${result.currentPrice.toFixed(4)}
        Action: ${result.action}
        Entry: $${result.entryPrice.toFixed(4)}
        Stop Loss: $${result.stopLoss.toFixed(4)}
        Take Profit: $${result.takeProfit.toFixed(4)}
        Conviction Score: ${result.convictionScore}%
        Risk/Reward: ${result.riskRewardRatio.toFixed(2)}:1

        Please provide:
        1. Additional technical insights
        2. Market structure considerations
        3. Risk management suggestions
        4. Potential catalysts or events to watch
        5. Alternative scenarios and their probabilities

        Format your response in a clear, concise manner with emojis for different sections.
      `;

      // Call the backend API to process with Gemini
      const response = await fetch('/api/enhance-analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          analysis: currentAnalysis,
          token: result.token,
          currentPrice: result.currentPrice,
          action: result.action,
          entryPrice: result.entryPrice,
          stopLoss: result.stopLoss,
          takeProfit: result.takeProfit,
          convictionScore: result.convictionScore,
          riskRewardRatio: result.riskRewardRatio,
          prompt: geminiPrompt
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}`);
      }

      const data = await response.json();

      // Update the result with the enhanced analysis
      setResult((prevResult) => ({
        ...prevResult!,
        gemini_analysis: data.enhanced_analysis
      }) as TradingSignal);
    } catch (error) {
      console.error('Error enhancing analysis with Gemini:', error);
      // Update the result with error information if needed
      setResult((prevResult) => ({
        ...prevResult!,
        gemini_analysis: `⚠️ Gemini Enhancement Failed: ${(error as Error).message}`
      }) as TradingSignal);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:64px_64px] opacity-20"></div>

      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mb-4">
            🧠 Trading Agent
          </h1>
          <p className="text-slate-400 text-xl">
            AI-Powered Smart Money Concepts Analysis
          </p>
        </div>

        {/* Input Controls */}
        <div className="max-w-2xl mx-auto mb-12">
          <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                🎯 Trading Analysis
              </CardTitle>
              <CardDescription className="text-slate-300">
                Configure your trading analysis parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-30">Token Symbol</label>
                  <select
                    title="Select token symbol"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    className="w-full p-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="SOL">SOL - Solana</option>
                    <option value="WIF">WIF - dogwifhat</option>
                    <option value="JUP">JUP - Jupiter</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-300">Blockchain</label>
                  <select
                    title="Select blockchain network"
                    value={chain}
                    onChange={(e) => setChain(e.target.value)}
                    className="w-full p-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="solana">Solana</option>
                    <option value="ethereum">Ethereum</option>
                    <option value="bsc">Binance Smart Chain</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button
                  onClick={handleAnalyze}
                  disabled={loading}
                  className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold py-3"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Analyzing...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      🚀 Start Analysis
                    </span>
                  )}
                </Button>
                <Button
                  onClick={handleDataComparison}
                  disabled={loading}
                  variant="outline"
                  className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white font-semibold py-3"
                >
                  📊 Data Comparison
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error Display */}
        {error && (
          <div className="max-w-4xl mx-auto mb-8">
            <Alert className="bg-red-900/50 border-red-700">
              <AlertDescription className="text-red-300">
                ❌ {error}
              </AlertDescription>
            </Alert>
          </div>
        )}

        {/* Full Trading Agent Console Display */}
        {result && (
          <div className="max-w-6xl mx-auto">
            <Card className="bg-black border-slate-600">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2 font-mono">
                  <span className="text-green-400">❯</span> Trading Agent Console
                </CardTitle>
              </CardHeader>
              <CardContent className="font-mono text-sm bg-gray-900 p-6 rounded">
                <pre className="text-green-400 whitespace-pre-line leading-relaxed">
                  {`================================================================================
🧠  GAME THEORY TRADE SIGNAL - ${result.token}

📊 Current Market
------------------------------------------------------------
  💰 Token: ${result.token}
  📊 Price: $${result.currentPrice.toFixed(4)}


🎯 Trading Recommendation
------------------------------------------------------------
  ${result.action === 'BUY' ? '📈' : result.action === 'SELL' ? '📉' : '⏸️'} ${result.action}


🧭 Entry & Targets
------------------------------------------------------------
  🔓 Entry Price: $${result.entryPrice.toFixed(4)}
  🛡️ Stop Loss: $${result.stopLoss.toFixed(4)} (${(((result.currentPrice - result.stopLoss) / result.currentPrice) * 100).toFixed(1)}%)
  🎯 Take Profit: $${result.takeProfit.toFixed(4)} (${(((result.takeProfit - result.currentPrice) / result.currentPrice) * 100).toFixed(1)}%)


⚖️ Risk Management
------------------------------------------------------------
  Risk/Reward: ${result.riskRewardRatio >= 2 ? '✅' : result.riskRewardRatio >= 1.5 ? '🟡' : '❌'} ${result.riskRewardRatio.toFixed(2)}:1


🔥 Conviction Score
------------------------------------------------------------
  ⭐ ${'█'.repeat(Math.round(result.convictionScore / 10))}${'░'.repeat(10 - Math.round(result.convictionScore / 10))} ${result.convictionScore}%

  ${result.strategy ? `🔮 Strategy: ${result.strategy}\n` : ''}

🔍 Analysis
------------------------------------------------------------
${result.reasoning}

${result.highProbabilitySetups && result.highProbabilitySetups.length > 0 ? `
🎯 HIGH-PROBABILITY SETUPS DETECTED (${result.highProbabilitySetups.length})

${result.highProbabilitySetups.map((setup, index) => `${index + 1}. ${setup.icon} ${setup.setupType} - ${setup.confidenceLevel}
   📈 Direction: ${setup.direction}
   📊 Probability: ${setup.probability}%
   🎯 Entry: ${setup.entryCriteria}
   🏆 Target: ${setup.target}
   ⚙️ Session: ${setup.session}
   🛡️ Risk Mgmt: ${setup.riskManagement}
   ✅ Confluence Factors:
${setup.confluenceFactors.map(factor => `      • ${factor}`).join('\n')}\n`).join('\n')}
` : ''}
${result.fabioAnalysis ? `
🏛️ Fabio Valentino Framework
------------------------------------------------------------
  Session: ${result.fabioAnalysis.session === 'New_York' ? '🗽 NY Session' :
                        result.fabioAnalysis.session === 'London' ? '🇬🇧 London Session' :
                          result.fabioAnalysis.session === 'Asian' ? '🌏 Asian Session' :
                            result.fabioAnalysis.session}
  Market State: ${result.fabioAnalysis.market_state}

  📊 Candlestick Patterns:
${result.candlestickDisplay ? `
    📊 LTF (5m):
${result.candlestickDisplay.ltf.map(pattern => `      • ${pattern}`).join('\n')}

    📊 HTF (1h):
${result.candlestickDisplay.htf.map(pattern => `      • ${pattern}`).join('\n')}

    📊 Daily:
${result.candlestickDisplay.daily.map(pattern => `      • ${pattern}`).join('\n')}
` : '    No significant patterns detected'}

  📈 Buying Pressure: ${result.fabioAnalysis.buying_pressure}
  📉 Selling Pressure: ${result.fabioAnalysis.selling_pressure}
  📊 CVD Trend: ${result.fabioAnalysis.cvd_trend}

  🎯 Trading Opportunities:
${result.tradingOpportunities ? result.tradingOpportunities.map(opp => `    ${opp.time} ${opp.status}
${opp.details.map(detail => `      • ${detail}`).join('\n')}`).join('\n\n') : '    ⏳ Waiting for optimal entry conditions'}

------------------------------------------------------------
  💡 Tip: Fabio Valentino strategy requires patience - wait for high-probability setups
` : ''}

🕐 Last updated: ${new Date(result.timestamp).toLocaleString()}

✅ Analysis complete
================================================================================`}
                </pre>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Data Comparison Display */}
        {dataComparison && showingComparison && (
          <div className="max-w-7xl mx-auto">
            <Card className="bg-slate-900/50 border-slate-700 backdrop-blur-sm mb-8">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2 font-mono">
                  <span className="text-blue-400">🔄</span> Data Processing Comparison
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowingComparison(false)}
                    className="ml-auto text-slate-400 hover:text-white"
                  >
                    ✕
                  </Button>
                </CardTitle>
                <CardDescription className="text-slate-300">
                  Shows all calculated data vs what gets sent to Gemini AI
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Full Calculated Data */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                      <span className="text-green-400">🔍</span> All Calculated Data
                    </h3>
                    <ScrollArea className="h-96 bg-slate-800/50 rounded-lg p-4">
                      <pre className="text-green-300 text-xs font-mono whitespace-pre-wrap">
                        {JSON.stringify(dataComparison.allCalculatedData, null, 2)}
                      </pre>
                    </ScrollArea>
                  </div>

                  {/* Gemini Payload */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                      <span className="text-purple-400">🤖</span> Data Sent to Gemini AI
                    </h3>
                    <ScrollArea className="h-96 bg-slate-800/50 rounded-lg p-4">
                      <pre className="text-purple-300 text-xs font-mono whitespace-pre-wrap">
                        {JSON.stringify(dataComparison.geminiPayload, null, 2)}
                      </pre>
                    </ScrollArea>
                  </div>
                </div>

                {/* Summary Stats */}
                <div className="mt-6 p-4 bg-slate-800/30 rounded-lg">
                  <h4 className="text-md font-semibold text-white mb-3 flex items-center gap-2">
                    <span className="text-yellow-400">📊</span> Data Summary:
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div className="bg-slate-800/50 p-3 rounded">
                      <span className="text-green-400">📈 OHLCV Data:</span><br />
                      LTF: {(dataComparison.allCalculatedData?.ohlcvData?.ltf?.length || 0)} candles<br />
                      HTF: {(dataComparison.allCalculatedData?.ohlcvData?.htf?.length || 0)} candles<br />
                      Daily: {(dataComparison.allCalculatedData?.ohlcvData?.daily?.length || 0)} candles
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded">
                      <span className="text-blue-400">📊 Analysis Data:</span><br />
                      Candlestick Patterns: 🕯️ Detected<br />
                      FVGs: {[
                        (dataComparison.allCalculatedData?.fvgs?.ltf?.length || 0),
                        (dataComparison.allCalculatedData?.fvgs?.htf?.length || 0),
                        (dataComparison.allCalculatedData?.fvgs?.daily?.length || 0)
                      ].reduce((a, b) => a + b, 0)} total{" "}
                      {dataComparison.allCalculatedData?.fvgs?.ltf?.length > 0 && `(${dataComparison.allCalculatedData?.fvgs?.ltf?.length} LTF)`}
                      {dataComparison.allCalculatedData?.fvgs?.htf?.length > 0 && `(${dataComparison.allCalculatedData?.fvgs?.htf?.length} HTF)`}<br />
                      Market Structure: ✓ Calculated<br />
                      Volume Analytics: ✓ Calculated
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded">
                      <span className="text-purple-400">🚀 Gemini Payload:</span><br />
                      Size: {JSON.stringify(dataComparison.geminiPayload).length} characters<br />
                      Includes: Technical indicators, FVGs, Market Structure, Session data
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-16 text-slate-500">
          <p className="text-sm">
            Powered by Advanced AI • Smart Money Concepts Analysis • Real-time Market Data
          </p>
        </div>
      </div>
    </div>
  )
}
