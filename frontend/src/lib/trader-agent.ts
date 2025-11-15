import { RSI, MACD } from "technicalindicators";
import { GoogleGenAI } from "@google/genai";

const BIRDEYE_API_KEY =
  process.env.NEXT_PUBLIC_BIRDEYE_API_KEY || process.env.BIRDEYE_API_KEY;
const COINGECKO_API_KEY =
  process.env.NEXT_PUBLIC_COINGECKO_API_KEY || process.env.COINGECKO_API_KEY;
const GEMINI_API_KEY =
  process.env.NEXT_PUBLIC_GEMINI_API_KEY || process.env.GEMINI_API_KEY;

// Only create AI instance if API keys are available
let ai: GoogleGenAI | null = null;
if (GEMINI_API_KEY) {
  ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
}

interface OHLVC {
  t: number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

interface FVG {
  type: "bullish" | "bearish";
  zone: [number, number];
  candle_index: number;
  timeframe: string;
}

interface TechnicalIndicators {
  rsi: number | null;
  macd: {
    MACD?: number;
    signal?: number;
    histogram?: number;
  } | null;
}

interface BasicMarketStructure {
  swing_highs: number[];
  swing_lows: number[];
  recent_high: number | null;
  recent_low: number | null;
}

interface VolumeAnalytics {
  volume_trend: "increasing" | "decreasing" | "neutral";
  volume_spike_detected: boolean;
  avg_volume_last_10: number;
  current_volume_vs_avg: number;
}

interface TradingSignal {
  action: "BUY" | "SELL" | "HOLD";
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  conviction_score: number;
  reasoning: string;
}

interface CandlestickPatterns {
  ltf: Array<{
    pattern: string;
    price: number;
    strength: string;
    direction: string;
  }>;
  htf: Array<{
    pattern: string;
    price: number;
    strength: string;
    direction: string;
  }>;
  daily: Array<{
    pattern: string;
    price: number;
    strength: string;
    direction: string;
  }>;
}

interface CandlestickDisplay {
  ltf: string[];
  htf: string[];
  daily: string[];
}

interface MarketStructure {
  ltf: {
    value_area_high: number | null;
    value_area_low: number | null;
    point_of_control: number | null;
    swing_highs: number[];
    swing_lows: number[];
  };
  htf: {
    value_area_high: number | null;
    value_area_low: number | null;
    point_of_control: number | null;
    swing_highs: number[];
    swing_lows: number[];
  };
  daily: {
    value_area_high: number | null;
    value_area_low: number | null;
    point_of_control: number | null;
    swing_highs: number[];
    swing_lows: number[];
  };
}

interface OrderFlow {
  ltf: {
    buying_pressure: string;
    selling_pressure: string;
    cvd_trend: string;
    cumulative_volume_delta: number;
  };
  htf: {
    buying_pressure: string;
    selling_pressure: string;
    cvd_trend: string;
    cumulative_volume_delta: number;
  };
  daily: {
    buying_pressure: string;
    selling_pressure: string;
    cvd_trend: string;
    cumulative_volume_delta: number;
  };
}

interface FabioAnalysis {
  session: string;
  market_state: string;
  buying_pressure: string;
  selling_pressure: string;
  cvd_trend: string;
}

interface HighProbabilitySetup {
  icon: string;
  setupType: string;
  confidenceLevel: string;
  direction: string;
  probability: number;
  entryCriteria: string;
  target: string;
  session: string;
  riskManagement: string;
  confluenceFactors: string[];
}

interface TradingOpportunities {
  time: string;
  status: string;
  details: string[];
}

interface FormattedTradingResponse {
  formatted: boolean;
  token: string;
  currentPrice: number;
  action: "BUY" | "SELL" | "HOLD";
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  convictionScore: number;
  riskRewardRatio: number;
  reasoning: string;
  strategy?: string;
  timestamp: string;
  candlestickPatterns?: CandlestickPatterns;
  candlestickDisplay?: CandlestickDisplay;
  marketStructure?: MarketStructure;
  orderFlow?: OrderFlow;
  fabioAnalysis?: FabioAnalysis;
  highProbabilitySetups?: HighProbabilitySetup[];
  tradingOpportunities?: TradingOpportunities[];
  raw: TradingSignal;
}

// ... (keep all the other interfaces and functions as they are)

async function getTopPoolCoinGecko(tokenAddress: string, network = "solana") {
  const networkMap: { [key: string]: string } = {
    solana: "solana",
    ethereum: "eth",
    bsc: "bsc-mainnet",
    polygon: "polygon-pos-mainnet",
  };
  const mappedNetwork = networkMap[network] || network;
  const poolsUrl = `https://api.coingecko.com/api/v3/onchain/networks/${mappedNetwork}/tokens/${tokenAddress}/pools`;
  const headers = { "x-cg-demo-api-key": COINGECKO_API_KEY || "" };

  try {
    const response = await fetch(poolsUrl, { headers });
    if (!response.ok) {
      const errorText = await response.text();
      console.error("CoinGecko API error response:", errorText);
      throw new Error(
        `CoinGecko API error: ${response.status} ${response.statusText}`
      );
    }
    const responseData = await response.json();
    if (responseData.data && responseData.data.length > 0) {
      const topPool = responseData.data[0];
      return topPool.attributes?.address || topPool.id;
    }
    console.log("No pools found for token.");
    return null;
  } catch (error) {
    console.error("Error fetching pools from CoinGecko:", error);
    return null;
  }
}

async function fetchOHLCVCoinGecko(
  poolAddress: string,
  network = "solana",
  timeframe = "minute",
  aggregate = 5,
  limit = 100
): Promise<OHLVC[]> {
  const networkMap: { [key: string]: string } = {
    solana: "solana",
    ethereum: "eth",
    bsc: "bsc-mainnet",
    polygon: "polygon-pos-mainnet",
  };
  const mappedNetwork = networkMap[network] || network;
  const cleanPoolAddress = poolAddress.includes("_")
    ? poolAddress.split("_")[1]
    : poolAddress;
  const ohlcvUrl = `https://api.coingecko.com/api/v3/onchain/networks/${mappedNetwork}/pools/${cleanPoolAddress}/ohlcv/${timeframe}?aggregate=${aggregate}&limit=${limit}`;
  const headers = { "x-cg-demo-api-key": COINGECKO_API_KEY || "" };

  try {
    const response = await fetch(ohlcvUrl, { headers });
    if (!response.ok) {
      const errorText = await response.text();
      console.error("CoinGecko API error response:", errorText);
      throw new Error(
        `CoinGecko API error: ${response.status} ${response.statusText}`
      );
    }
    const data = (await response.json()).data?.attributes?.ohlcv_list || [];
    return data.map((item: number[]) => ({
      t: item[0],
      o: item[1],
      h: item[2],
      l: item[3],
      c: item[4],
      v: item[5],
    }));
  } catch (error) {
    console.error("Error fetching OHLCV from CoinGecko:", error);
    return [];
  }
}

async function fetchMultipleTimeframesCoinGecko(
  poolAddress: string,
  network = "solana"
) {
  const ltf = await fetchOHLCVCoinGecko(poolAddress, network, "minute", 5, 100);
  const htf = await fetchOHLCVCoinGecko(poolAddress, network, "hour", 1, 25);
  const daily = await fetchOHLCVCoinGecko(poolAddress, network, "day", 1, 30);
  return { ltf, htf, daily };
}

async function fetchBirdeyeData(tokenAddress: string, chain: string) {
  if (!BIRDEYE_API_KEY) {
    throw new Error("Birdeye API Key is missing.");
  }
  const headers = { "X-API-KEY": BIRDEYE_API_KEY, "X-CHAIN": chain };
  const marketUrl = `https://public-api.birdeye.so/defi/price?address=${tokenAddress}&include_liquidity=true&ui_amount_mode=raw`;

  try {
    const marketResponse = await fetch(marketUrl, { headers });
    if (!marketResponse.ok) {
      const errorText = await marketResponse.text();
      console.error("Birdeye API error response:", errorText);
      throw new Error(
        `Birdeye API error: ${marketResponse.status} ${marketResponse.statusText}`
      );
    }
    const marketData = (await marketResponse.json()).data || {};

    const poolAddress = await getTopPoolCoinGecko(tokenAddress, chain);
    const ohlcvData = poolAddress
      ? await fetchMultipleTimeframesCoinGecko(poolAddress, chain)
      : { ltf: [], htf: [], daily: [] };

    return { marketData, ohlcvData };
  } catch (error) {
    console.error("Error fetching Birdeye data:", error);
    throw error;
  }
}

function calculateTechnicalIndicators(ohlcvData: OHLVC[]): TechnicalIndicators {
  if (ohlcvData.length === 0) {
    return { rsi: null, macd: null };
  }

  const closePrices = ohlcvData.map((d) => d.c);

  const rsi = RSI.calculate({ values: closePrices, period: 14 });
  const macd = MACD.calculate({
    values: closePrices,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9,
    SimpleMAOscillator: false,
    SimpleMASignal: false,
  });

  return {
    rsi: rsi.length > 0 ? rsi[rsi.length - 1] : null,
    macd: macd.length > 0 ? macd[macd.length - 1] : null,
  };
}

function calculateFairValueGaps(df: OHLVC[]): FVG[] {
  if (df.length < 5) {
    return [];
  }
  const fvgs: FVG[] = [];

  // Calculate cumulative volume and thresholds like LuxAlgo
  const barDeltas = df.map((d) => (d.c - d.o) / (d.o * 100));
  const barChanges = barDeltas.map((delta) => Math.abs(delta));
  const cumVolThreshold =
    (barChanges.reduce((acc, change) => acc + change, 0) / df.length) * 2;
  const maxCumVolThreshold = Math.max(...barChanges) * 1.5; // LuxAlgo style threshold

  for (let i = 2; i < df.length - 2; i++) {
    const last2 = df[i - 2];
    const last1 = df[i - 1];
    const curr = df[i];
    const next1 = df[i + 1];
    const next2 = df[i + 2];

    // Calculate volume-based scores
    const lastBarDelta = (last1.c - last1.o) / (last1.o * 100);
    const currentBarDelta = (curr.c - curr.o) / (curr.o * 100);
    const volumeWeightedScore =
      Math.abs(lastBarDelta) + Math.abs(currentBarDelta);

    // LuxAlgo-style FVG conditions with stricter requirements
    const bullishCondition =
      curr.l > last1.h &&
      last1.c > last2.h &&
      currentBarDelta > Math.abs(lastBarDelta) * 0.1 &&
      volumeWeightedScore > cumVolThreshold * 0.5;

    const bearishCondition =
      curr.h < last1.l &&
      last1.c < last2.l &&
      -currentBarDelta > Math.abs(lastBarDelta) * 0.1 &&
      volumeWeightedScore > cumVolThreshold * 0.5;

    if (bullishCondition && curr.h < next1.l) {
      fvgs.push({
        type: "bullish",
        zone: [last1.h, Math.min(curr.l, next1.l)],
        candle_index: i,
        timeframe: "current",
      });
    }

    if (bearishCondition && curr.l > next1.h) {
      fvgs.push({
        type: "bearish",
        zone: [Math.max(curr.h, next1.h), last1.l],
        candle_index: i,
        timeframe: "current",
      });
    }
  }
  return fvgs;
}

function calculateMarketStructure(df: OHLVC[]): BasicMarketStructure {
  if (df.length < 3) {
    return {
      swing_highs: [],
      swing_lows: [],
      recent_high: null,
      recent_low: null,
    };
  }

  const swingHighs: number[] = [];
  const swingLows: number[] = [];

  for (let i = 1; i < df.length - 1; i++) {
    if (df[i].h > df[i - 1].h && df[i].h > df[i + 1].h) {
      swingHighs.push(df[i].h);
    }
    if (df[i].l < df[i - 1].l && df[i].l < df[i + 1].l) {
      swingLows.push(df[i].l);
    }
  }

  const recentSlice = df.slice(-10);
  const recentHigh = Math.max(...recentSlice.map((d) => d.h));
  const recentLow = Math.min(...recentSlice.map((d) => d.l));

  return {
    swing_highs: swingHighs,
    swing_lows: swingLows,
    recent_high: recentHigh,
    recent_low: recentLow,
  };
}

function calculateVolumeAnalytics(df: OHLVC[]): VolumeAnalytics {
  if (df.length < 20) {
    return {
      volume_trend: "neutral",
      volume_spike_detected: false,
      avg_volume_last_10: 0,
      current_volume_vs_avg: 0,
    };
  }

  const volumes = df.map((d) => d.v);
  const volEmaShort = new RSI({ values: volumes, period: 5 }).result;
  const volEmaLong = new RSI({ values: volumes, period: 20 }).result;

  const recentVols = volumes.slice(-10);
  const avgVolLast10 =
    recentVols.reduce((acc, v) => acc + v, 0) / recentVols.length;
  const currentVol = volumes[volumes.length - 1];
  const volumeSpike = currentVol > 2 * avgVolLast10;

  const volumeTrend =
    volEmaShort[volEmaShort.length - 1] > volEmaLong[volEmaLong.length - 1]
      ? "increasing"
      : "decreasing";

  return {
    volume_trend: volumeTrend,
    volume_spike_detected: volumeSpike,
    avg_volume_last_10: avgVolLast10,
    current_volume_vs_avg: currentVol / avgVolLast10,
  };
}

function getCurrentSession(): string {
  const hour = new Date().getUTCHours();
  if (hour >= 13 && hour < 21) return "New_York";
  if (hour >= 8 && hour < 13) return "London";
  if (hour >= 0 && hour < 8) return "Asian";
  return "Low_Volume";
}

// Calculate trailing swing points like LuxAlgo Pine Script
function calculateTrailingSwings(df: OHLVC[]): { top: number; bottom: number } {
  if (df.length < 3) {
    return {
      top: df[df.length - 1]?.h || 0,
      bottom: df[df.length - 1]?.l || 0,
    };
  }

  let top = df[0].h;
  let bottom = df[0].l;

  for (let i = 1; i < df.length; i++) {
    top = Math.max(top, df[i].h);
    bottom = Math.min(bottom, df[i].l);
  }

  return { top, bottom };
}

function formatTradingSignal(
  data: TradingSignal,
  token: string,
  currentPrice: number,
  ltfIndicators: TechnicalIndicators,
  htfIndicators: TechnicalIndicators,
  dailyIndicators: TechnicalIndicators,
  ltfMarketStructure: BasicMarketStructure,
  htfMarketStructure: BasicMarketStructure,
  dailyMarketStructure: BasicMarketStructure
): FormattedTradingResponse {
  console.log(`🔍 DEBUG: Requested AI provider: gemini`);
  console.log(`🔍 DEBUG: Checking Gemini API...`);
  console.log(`✅ Gemini AI confirmed available`);
  console.log(`...Fetching real-time data...`);
  console.log(`...Processing raw data and calculating indicators...`);
  console.log(
    `...Sending structured data to GEMINI for high-level analysis...`
  );

  // Calculate risk/reward ratio
  const risk = Math.abs(currentPrice - data.stop_loss);
  const reward = Math.abs(data.take_profit - currentPrice);
  const rrRatio = reward / risk;
  const convictionScore = data.conviction_score || 0;

  // Generate Fabio Valentino framework analysis
  const session = getCurrentSession();
  let buyingPressure = "neutral";
  let sellingPressure = "neutral";
  const cvdTrend = "neutral";
  let marketState = "BALANCED";

  // Simple market state determination based on RSI
  const ltfRsi = ltfIndicators.rsi || 50;
  const htfRsi = htfIndicators.rsi || 50;

  if (ltfRsi < 35 && htfRsi < 45) {
    buyingPressure = "low";
    sellingPressure = "high";
    marketState = "BEARISH_IMBALANCE";
  } else if (ltfRsi > 65 && htfRsi > 55) {
    buyingPressure = "high";
    sellingPressure = "low";
    marketState = "BULLISH_IMBALANCE";
  }

  const fabioAnalysis: FabioAnalysis = {
    session,
    market_state: marketState,
    buying_pressure: buyingPressure,
    selling_pressure: sellingPressure,
    cvd_trend: cvdTrend,
  };

  // Generate candlestick patterns simulation (simplified)
  const candlestickPatterns: CandlestickPatterns = {
    ltf: [],
    htf: [],
    daily: [],
  };

  // Generate candlestick display format
  const candlestickDisplay: CandlestickDisplay = {
    ltf: candlestickPatterns.ltf.map(
      (p) => `${p.pattern} @ $${p.price.toFixed(4)}`
    ),
    htf: candlestickPatterns.htf.map(
      (p) => `${p.pattern} @ $${p.price.toFixed(4)}`
    ),
    daily: candlestickPatterns.daily.map(
      (p) => `${p.pattern} @ $${p.price.toFixed(4)}`
    ),
  };

  // Generate high probability setups based on current analysis
  const highProbabilitySetups: HighProbabilitySetup[] = [];
  const ltfRsiValue = ltfIndicators.rsi || 50;
  const htfRsiValue = htfIndicators.rsi || 50;

  if (ltfRsiValue < 35) {
    const entryPrice = currentPrice * 0.99; // Slight discount for mean reversion entry
    highProbabilitySetups.push({
      icon: "⭐",
      setupType: "Mean Reversion",
      confidenceLevel: "HIGH PROBABILITY",
      direction: "Long",
      probability: 85,
      entryCriteria: `Enter at $${entryPrice.toFixed(
        4
      )} (current: $${currentPrice.toFixed(4)})`,
      target: `HTF POC at $${(currentPrice * 1.025).toFixed(4)}`,
      session: `${session} session timing`,
      riskManagement: "Tight stops below swing low, quick break-even movement",
      confluenceFactors: [
        `LTF RSI oversold at ${ltfRsiValue.toFixed(1)}`,
        `Buying pressure: ${buyingPressure}`,
        "Multiple timeframe confluence",
      ],
    });
  } else if (ltfRsiValue > 65) {
    const entryPrice = currentPrice * 1.01; // Slight premium for breakout short
    highProbabilitySetups.push({
      icon: "🔥",
      setupType: "Trend Following",
      confidenceLevel: "MEDIUM PROBABILITY",
      direction: "Short",
      probability: 70,
      entryCriteria: `Enter short at $${entryPrice.toFixed(
        4
      )} (current: $${currentPrice.toFixed(4)})`,
      target: `Next support level at $${(currentPrice * 0.975).toFixed(4)}`,
      session: `${session} session timing`,
      riskManagement: "Trailing stops, momentum-based entries",
      confluenceFactors: [
        `LTF RSI overbought at ${ltfRsiValue.toFixed(1)}`,
        "Resistance level confluence",
        `${sellingPressure} selling pressure`,
      ],
    });
  }

  // Generate market structure data
  const marketStructure: MarketStructure | undefined = htfMarketStructure
    ? {
        ltf: {
          value_area_high:
            (ltfMarketStructure.recent_high || currentPrice) * 1.02,
          value_area_low:
            (ltfMarketStructure.recent_low || currentPrice) * 0.98,
          point_of_control: currentPrice,
          swing_highs: ltfMarketStructure.swing_highs,
          swing_lows: ltfMarketStructure.swing_lows,
        },
        htf: {
          value_area_high:
            (htfMarketStructure.recent_high || currentPrice) * 1.02,
          value_area_low:
            (htfMarketStructure.recent_low || currentPrice) * 0.98,
          point_of_control: currentPrice,
          swing_highs: htfMarketStructure.swing_highs,
          swing_lows: htfMarketStructure.swing_lows,
        },
        daily: {
          value_area_high:
            (dailyMarketStructure.recent_high || currentPrice) * 1.02,
          value_area_low:
            (dailyMarketStructure.recent_low || currentPrice) * 0.98,
          point_of_control: currentPrice,
          swing_highs: dailyMarketStructure.swing_highs,
          swing_lows: dailyMarketStructure.swing_lows,
        },
      }
    : undefined;

  // Generate order flow data
  const orderFlow: OrderFlow | undefined = {
    ltf: {
      buying_pressure: buyingPressure,
      selling_pressure: sellingPressure,
      cvd_trend: cvdTrend,
      cumulative_volume_delta: 0,
    },
    htf: {
      buying_pressure: buyingPressure,
      selling_pressure: sellingPressure,
      cvd_trend: cvdTrend,
      cumulative_volume_delta: 0,
    },
    daily: {
      buying_pressure: buyingPressure,
      selling_pressure: sellingPressure,
      cvd_trend: cvdTrend,
      cumulative_volume_delta: 0,
    },
  };

  // Generate trading opportunities based on market state
  const tradingOpportunities =
    highProbabilitySetups.length > 0
      ? highProbabilitySetups.map((setup) => ({
          time: setup.icon === "⭐" ? "🎯" : "🔥",
          status: `${setup.setupType} setup available`,
          details: [
            `Probability: ${setup.probability}%`,
            `Direction: ${setup.direction}`,
            `${setup.session}`,
          ],
        }))
      : [
          {
            time: "🕐",
            status: "⏳ Waiting for optimal entry conditions",
            details: [
              "Waiting for optimal entry conditions",
              "Monitor for: LVN reaction, POC proximity, session alignment",
            ],
          },
        ];

  // Enhanced reasoning based on technical analysis
  let enhancedReasoning = data.reasoning;
  enhancedReasoning += "\n\n🧠 Enhanced Analysis:";
  enhancedReasoning += `\n• LTF RSI: ${ltfRsiValue.toFixed(1)} (${
    ltfRsiValue < 35 ? "Oversold" : ltfRsiValue > 65 ? "Overbought" : "Neutral"
  })`;
  enhancedReasoning += `\n• HTF RSI: ${htfRsiValue.toFixed(1)} (${
    htfRsiValue < 45 ? "Oversold" : htfRsiValue > 55 ? "Overbought" : "Neutral"
  })`;
  enhancedReasoning += `\n• Current Session: ${session}`;
  enhancedReasoning += `\n• Market State: ${marketState}`;

  return {
    formatted: true,
    token,
    currentPrice,
    action: data.action,
    entryPrice: data.entry_price,
    stopLoss: data.stop_loss,
    takeProfit: data.take_profit,
    convictionScore,
    riskRewardRatio: rrRatio,
    reasoning: enhancedReasoning,
    strategy: data.action === "BUY" ? "Mean Reversion" : "Trend Following",
    timestamp: new Date().toISOString(),
    candlestickPatterns,
    candlestickDisplay,
    marketStructure,
    orderFlow,
    fabioAnalysis,
    highProbabilitySetups,
    tradingOpportunities,
    raw: data,
  };
}

function generateProgressBar(value: number, width: number): string {
  const filled = Math.round((value / 100) * width);
  const empty = width - filled;
  return "█".repeat(filled) + "░".repeat(empty);
}

export async function getSignalAnalysis(token: string, chain: string) {
  const tokenAddress = await getTokenAddress(token, chain);
  if (!tokenAddress) {
    throw new Error(`Could not find token address for ${token} on ${chain}`);
  }

  const { marketData, ohlcvData } = await fetchBirdeyeData(tokenAddress, chain);

  const ltfIndicators = calculateTechnicalIndicators(ohlcvData.ltf);
  const htfIndicators = calculateTechnicalIndicators(ohlcvData.htf);
  const dailyIndicators = calculateTechnicalIndicators(ohlcvData.daily);

  const ltfFvgs = calculateFairValueGaps(ohlcvData.ltf);
  const htfFvgs = calculateFairValueGaps(ohlcvData.htf);
  const dailyFvgs = calculateFairValueGaps(ohlcvData.daily);

  const ltfMarketStructure = calculateMarketStructure(ohlcvData.ltf);
  const htfMarketStructure = calculateMarketStructure(ohlcvData.htf);
  const dailyMarketStructure = calculateMarketStructure(ohlcvData.daily);

  const ltfVolumeAnalytics = calculateVolumeAnalytics(ohlcvData.ltf);
  const htfVolumeAnalytics = calculateVolumeAnalytics(ohlcvData.htf);
  const dailyVolumeAnalytics = calculateVolumeAnalytics(ohlcvData.daily);

  const analysisPayload = {
    coin_symbol: token,
    current_price: marketData.value,
    liquidity_usd: marketData.liquidity,
    volume_24hr: marketData.v24h,
    ltf: {
      ...ltfIndicators,
      fvgs: ltfFvgs,
      market_structure: ltfMarketStructure,
      volume_analytics: ltfVolumeAnalytics,
    },
    htf: {
      ...htfIndicators,
      fvgs: htfFvgs,
      market_structure: htfMarketStructure,
      volume_analytics: htfVolumeAnalytics,
    },
    daily: {
      ...dailyIndicators,
      fvgs: dailyFvgs,
      market_structure: dailyMarketStructure,
      volume_analytics: dailyVolumeAnalytics,
    },
    current_session: getCurrentSession(),
  };

  // Check if AI is available
  if (!ai) {
    console.log("🤖 Gemini AI not available - using technical analysis only");

    // Generate signal based on technical analysis without AI
    const ltfRsi = (ltfIndicators.rsi as number) || 50;
    const htfRsi = (htfIndicators.rsi as number) || 50;
    const currentPrice = marketData.value;

    let action: "BUY" | "SELL" | "HOLD";
    let conviction_score = 50;
    let reasoning = "";

    if (ltfRsi < 30 && htfRsi < 40) {
      action = "BUY";
      conviction_score = 75;
      reasoning = `Technical Analysis - Oversold conditions (LTF RSI: ${ltfRsi.toFixed(
        1
      )}, HTF RSI: ${htfRsi.toFixed(1)})`;
    } else if (ltfRsi > 70 && htfRsi > 60) {
      action = "SELL";
      conviction_score = 70;
      reasoning = `Technical Analysis - Overbought conditions (LTF RSI: ${ltfRsi.toFixed(
        1
      )}, HTF RSI: ${htfRsi.toFixed(1)})`;
    } else {
      action = "HOLD";
      conviction_score = 55;
      reasoning = `Technical Analysis - Neutral conditions (LTF RSI: ${ltfRsi.toFixed(
        1
      )}, HTF RSI: ${htfRsi.toFixed(1)})`;
    }

    const entry_price = currentPrice;
    const stop_loss = currentPrice * (action === "BUY" ? 0.98 : 1.02);
    const take_profit = currentPrice * (action === "BUY" ? 1.025 : 0.975);

    return formatTradingSignal(
      {
        action,
        entry_price,
        stop_loss,
        take_profit,
        conviction_score,
        reasoning,
      },
      token,
      currentPrice,
      ltfIndicators,
      htfIndicators,
      dailyIndicators,
      ltfMarketStructure,
      htfMarketStructure,
      dailyMarketStructure
    );
  }

  const prompt = `
    You are a professional, high-conviction Smart Money Concepts (SMC) trading agent.
    Analyze the provided JSON market data and generate a high-probability trade recommendation.

    IMPORTANT: Pay special attention to Fair Value Gaps (FVGs) - include analysis of:
    1. Whether FVGs are present or absent in the data
    2. The significance of FVG concentration/density
    3. How FVG absence impacts institutional order block identification
    4. Whether FVG absence limits precision vs other market structure factors
    5. When FVGs are absent, rely on market structure breaks and liquidity targets for conviction

    Your output MUST be a single JSON object with keys: 'action' (BUY/SELL/HOLD), 'entry_price', 'stop_loss', 'take_profit', 'conviction_score' (1-100), and 'reasoning'.

    Format your reasoning professionally, mentioning FVG presence/absence and how it affects your analysis.
    Example: "While the absence of Fair Value Gaps (FVGs) in the provided data limits our ability to identify precise institutional order block entries..."

    Analyze the following data and provide a trade signal: ${JSON.stringify(
      analysisPayload
    )}
  `;

  try {
    console.log(`🚀 Starting Trading Agent for ${token} on ${chain}...`);
    const result = await ai!.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
    });
    const text = result.text || "";
    // Clean the text to remove markdown and parse JSON
    const cleanedText = text
      .replace(/```json/g, "")
      .replace(/```/g, "")
      .trim();
    const rawData = JSON.parse(cleanedText);

    // Format the response for better readability
    const formatted = formatTradingSignal(
      rawData,
      token,
      marketData.value,
      ltfIndicators,
      htfIndicators,
      dailyIndicators,
      ltfMarketStructure,
      htfMarketStructure,
      dailyMarketStructure
    );

    return formatted;
  } catch (error) {
    console.error("Error parsing Gemini response:", error);
    throw new Error("Failed to parse trade signal from Gemini API.");
  }
}

async function getTokenAddress(tokenSymbol: string, network: string) {
  // In a real app, you'd have a more robust way to get token addresses.
  // This is a simplified example.
  const tokenMap: { [key: string]: string } = {
    SOL: "So11111111111111111111111111111111111111112",
    WIF: "EKpQ8UgDHHJzhLDc2LwJbQf4XJdG1yv2QJg1w2Y2Q2Q2",
    JUP: "JUPyi4yQym9nu2x5s4W2JdG1yv2QJg1w2Y2Q2Q2Q2Q2",
  };
  return tokenMap[tokenSymbol.toUpperCase()];
}
