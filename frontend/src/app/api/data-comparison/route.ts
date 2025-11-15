/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-require-imports */
import { NextRequest, NextResponse } from "next/server";

// Local function to get token address (avoiding dependency on lib export)
async function getTokenAddress(tokenSymbol: string, network: string) {
  // Simplified token map - can be expanded
  const tokenMap: { [key: string]: string } = {
    SOL: "So11111111111111111111111111111111111111112",
    WIF: "EKpQ8UgDHHJzhLDc2LwJbQf4XJdG1yv2QJg1w2Y2Q2Q2",
    JUP: "JUPyi4yQym9nu2x5s4W2JdG1yv2QJg1w2Y2Q2Q2Q2Q2",
  };
  return tokenMap[tokenSymbol.toUpperCase()] || null;
}

// Type definitions
interface OHLVCData {
  t: number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

interface TechnicalIndicators {
  rsi: number | null;
  macd: {
    MACD?: number;
    signal?: number;
    histogram?: number;
  } | null;
}

async function getTopPoolCoinGecko(tokenAddress: string, network = "solana") {
  const networkMap: { [key: string]: string } = {
    solana: "solana",
    ethereum: "eth",
    bsc: "bsc-mainnet",
    polygon: "polygon-pos-mainnet",
  };
  const mappedNetwork = networkMap[network] || network;
  const poolsUrl = `https://api.coingecko.com/api/v3/onchain/networks/${mappedNetwork}/tokens/${tokenAddress}/pools`;
  const headers = {
    "x-cg-demo-api-key": process.env.NEXT_PUBLIC_COINGECKO_API_KEY || "",
  };

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
): Promise<OHLVCData[]> {
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
  const headers = {
    "x-cg-demo-api-key": process.env.NEXT_PUBLIC_COINGECKO_API_KEY || "",
  };

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

async function fetchBirdeyeData(
  tokenAddress: string,
  chain: string,
  token: string
) {
  const url = new URL("https://public-api.birdeye.so/defi/price");
  url.searchParams.set("address", tokenAddress);
  url.searchParams.set("include_liquidity", "true");
  url.searchParams.set("ui_amount_mode", "raw");

  const headers = {
    "X-API-KEY": process.env.NEXT_PUBLIC_BIRDEYE_API_KEY || "",
    "X-CHAIN": chain,
  };

  // Set a shorter timeout (5 seconds instead of default ~30s)
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);

  const marketResponse = await fetch(url.toString(), {
    headers,
    signal: controller.signal,
  });

  clearTimeout(timeoutId);

  if (!marketResponse.ok) {
    const errorText = await marketResponse.text();
    console.error("Birdeye API error response:", errorText);
    throw new Error(
      `Birdeye API error: ${marketResponse.status} ${marketResponse.statusText}`
    );
  }

  const marketData = (await marketResponse.json()).data || {};
  let ohlcvData: any = { ltf: [], htf: [], daily: [] };

  // Fetch OHLCV data - no fallbacks, fail if unavailable
  console.log(`Fetching OHLCV data from CoinGecko...`);
  const poolAddress = await getTopPoolCoinGecko(tokenAddress, chain);
  if (!poolAddress) {
    throw new Error(
      `No trading pool found for ${token} on ${chain}. Market liquidity data unavailable.`
    );
  }

  ohlcvData = await fetchMultipleTimeframesCoinGecko(poolAddress, chain);
  console.log(`Successfully fetched OHLCV data`);

  return { marketData, ohlcvData };
}

function calculateTechnicalIndicators(ohlcvData: any[]) {
  if (ohlcvData.length === 0) return { rsi: null, macd: null };

  const closePrices = ohlcvData.map((d) => d.c);
  const { RSI, MACD } = require("technicalindicators");

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

function calculateFairValueGaps(df: any[]): any[] {
  if (df.length < 3) {
    return [];
  }
  const fvgs: any[] = [];

  // Simplified FVG detection - key condition: gap in price action that can be filled
  for (let i = 1; i < df.length; i++) {
    const previous = df[i - 1];
    const current = df[i];

    // Bullish FVG: Current low leaves a gap above previous high
    if (current.l > previous.h) {
      fvgs.push({
        type: "bullish",
        zone: [previous.h, current.l],
        price_level: current.l,
        candle_index: i,
        timeframe: "current",
        description: `Bullish FVG: Price gap between ${previous.h.toFixed(
          4
        )} and ${current.l.toFixed(4)}`,
      });
    }

    // Bearish FVG: Current high leaves a gap below previous low
    if (current.h < previous.l) {
      fvgs.push({
        type: "bearish",
        zone: [current.h, previous.l],
        price_level: current.h,
        candle_index: i,
        timeframe: "current",
        description: `Bearish FVG: Price gap between ${current.h.toFixed(
          4
        )} and ${previous.l.toFixed(4)}`,
      });
    }
  }

  return fvgs;
}

function calculateMarketStructure(df: any[]): any {
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

function calculateVolumeAnalytics(df: any[]): any {
  if (df.length < 20) {
    return {
      volume_trend: "neutral",
      volume_spike_detected: false,
      avg_volume_last_10: 0,
      current_volume_vs_avg: 0,
    };
  }

  const volumes = df.map((d) => d.v);
  const { RSI } = require("technicalindicators");
  const volEmaShort = RSI.calculate({ values: volumes, period: 5 });
  const volEmaLong = RSI.calculate({ values: volumes, period: 20 });

  const recentVols = volumes.slice(-10);
  const avgVolLast10 =
    recentVols.reduce((acc, v) => acc + v, 0) / recentVols.length;
  const currentVol = volumes[volumes.length - 1];
  const volumeSpike = currentVol > 2 * avgVolLast10;

  let volumeTrend = "neutral";
  if (
    volEmaShort &&
    volEmaLong &&
    volEmaShort.length > 0 &&
    volEmaLong.length > 0
  ) {
    volumeTrend =
      volEmaShort[volEmaShort.length - 1] > volEmaLong[volEmaLong.length - 1]
        ? "increasing"
        : "decreasing";
  }

  return {
    volume_trend: volumeTrend,
    volume_spike_detected: volumeSpike,
    avg_volume_last_10: avgVolLast10,
    current_volume_vs_avg: currentVol / avgVolLast10,
  };
}

function calculateCandlestickPatterns(df: any[]): any[] {
  if (df.length < 3) return [];

  const patterns: any[] = [];
  const minPatternStrength = 0.002; // Minimum pattern strength threshold

  for (let i = 1; i < df.length; i++) {
    const current = df[i];
    const previous = df[i - 1];

    // Skip if candles don't have minimum movement
    const currentRange = Math.abs(current.h - current.l);
    if (currentRange < minPatternStrength) continue;

    // Bullish Engulfing Pattern
    if (i >= 1) {
      const isPreviousBearish = previous.c < previous.o;
      const isCurrentBullish = current.c > current.o;
      const bodyEngulfing =
        current.o <= previous.o &&
        current.c >= previous.c &&
        Math.abs(current.c - current.o) > Math.abs(previous.c - previous.o);

      if (isPreviousBearish && isCurrentBullish && bodyEngulfing) {
        patterns.push({
          pattern_type: "bullish_engulfing",
          candle_index: i,
          timeframe: "current",
          strength: "high",
          price: current.c,
          description:
            "Bullish engulfing pattern detected - potential bullish reversal",
        });
      }
    }

    // Bearish Engulfing Pattern
    if (i >= 1) {
      const isPreviousBullish = previous.c > previous.o;
      const isCurrentBearish = current.c < current.o;
      const bodyEngulfing =
        current.o >= previous.o &&
        current.c <= previous.c &&
        Math.abs(current.c - current.o) > Math.abs(previous.c - previous.o);

      if (isPreviousBullish && isCurrentBearish && bodyEngulfing) {
        patterns.push({
          pattern_type: "bearish_engulfing",
          candle_index: i,
          timeframe: "current",
          strength: "high",
          price: current.c,
          description:
            "Bearish engulfing pattern detected - potential bearish reversal",
        });
      }
    }

    // Outside Bar (volatility expansion)
    if (i >= 1) {
      const currentHigh = current.h;
      const currentLow = current.l;
      const previousHigh = previous.h;
      const previousLow = previous.l;

      if (
        (currentHigh > previousHigh && currentLow < previousLow) ||
        (currentHigh >= previousHigh &&
          currentLow < previousLow &&
          Math.abs(currentHigh - currentLow) >
            1.5 * Math.abs(previousHigh - previousLow))
      ) {
        patterns.push({
          pattern_type: "outside_bar",
          candle_index: i,
          timeframe: "current",
          strength: "medium",
          price: current.c,
          description: "Outside bar pattern detected - volatility expansion",
        });
      }
    }

    // Gravestone Doji Pattern
    if (current.c === current.o || Math.abs(current.c - current.o) < 0.0001) {
      const upperWick = Math.abs(current.h - Math.max(current.c, current.o));
      const lowerWick = Math.abs(Math.min(current.c, current.o) - current.l);
      const totalRange = current.h - current.l;

      if (upperWick > totalRange * 0.5 && lowerWick < totalRange * 0.1) {
        patterns.push({
          pattern_type: "gravestone_doji",
          candle_index: i,
          timeframe: "current",
          strength: "high",
          price: current.h,
          description:
            "Gravestone doji detected - potential rejection at higher levels",
        });
      }
    }

    // Evening Star Pattern (3 candle pattern)
    if (i >= 2 && df[i - 1]) {
      const third = current;
      const second = df[i - 1];
      const first = df[i - 2];

      const firstBullish = first.c > first.o;
      const thirdBearish = third.c < third.o;
      const secondStar =
        Math.abs(second.c - second.o) < (second.h - second.l) * 0.3;

      if (
        firstBullish &&
        thirdBearish &&
        secondStar &&
        third.l < Math.min(first.c, second.c)
      ) {
        patterns.push({
          pattern_type: "evening_star",
          candle_index: i,
          timeframe: "current",
          strength: "high",
          price: current.c,
          description:
            "Evening star pattern detected - potential bearish reversal",
        });
      }
    }
  }

  return patterns;
}

function generateSampleOHLCVData(tokenAddress: string) {
  // Generate sample OHLCV data for demonstration when APIs are unavailable
  const basePrice = 140.0; // Sample SOL price
  const currentTime = Date.now();

  const generateCandle = (timestamp: number, index: number) => {
    const base =
      basePrice + Math.sin(index * 0.1) * 2 + (Math.random() - 0.5) * 0.5;
    const volatility = base * 0.005; // 0.5% volatility
    const high = base + Math.abs(Math.random()) * volatility;
    const low = base - Math.abs(Math.random()) * volatility;
    const open = base + (Math.random() - 0.5) * volatility;
    const close = base + (Math.random() - 0.5) * volatility;
    const volume = 1000000 + Math.random() * 5000000; // Sample volume

    return {
      t: timestamp,
      o: Math.max(open, low, 0),
      h: high,
      l: Math.min(low, open, close, high),
      c: close,
      v: volume,
    };
  };

  const ltf: OHLVCData[] = [];
  const htf: OHLVCData[] = [];
  const daily: OHLVCData[] = [];

  // Generate LTF (5-minute) candles
  for (let i = 0; i < 100; i++) {
    ltf.push(generateCandle(currentTime - i * 300000, i)); // 5 minutes ago
  }

  // Generate HTF (1-hour) candles
  for (let i = 0; i < 25; i++) {
    htf.push(generateCandle(currentTime - i * 3600000, i)); // 1 hour ago
  }

  // Generate Daily candles
  for (let i = 0; i < 30; i++) {
    daily.push(generateCandle(currentTime - i * 86400000, i)); // 1 day ago
  }

  return { ltf: ltf.reverse(), htf: htf.reverse(), daily: daily.reverse() };
}

function getCurrentSession(): string {
  const hour = new Date().getUTCHours();
  if (hour >= 13 && hour < 21) return "New_York";
  if (hour >= 8 && hour < 13) return "London";
  if (hour >= 0 && hour < 8) return "Asian";
  return "Low_Volume";
}

export async function POST(request: NextRequest) {
  try {
    const { token, chain } = await request.json();

    console.log(`🔍 Fetching data for ${token} on ${chain}...`);

    const tokenAddress = await getTokenAddress(token, chain);
    if (!tokenAddress) {
      throw new Error(`Could not find token address for ${token} on ${chain}`);
    }

    console.log(`📊 Token address: ${tokenAddress}`);

    const { marketData, ohlcvData } = await fetchBirdeyeData(
      tokenAddress,
      chain,
      token
    );

    console.log(`💰 Market data:`, marketData);
    console.log(
      `📈 OHLCV data points - LTF: ${ohlcvData.ltf.length}, HTF: ${ohlcvData.htf.length}, Daily: ${ohlcvData.daily.length}`
    );

    // Calculate all indicators
    const ltfIndicators = calculateTechnicalIndicators(ohlcvData.ltf);
    const htfIndicators = calculateTechnicalIndicators(ohlcvData.htf);
    const dailyIndicators = calculateTechnicalIndicators(ohlcvData.daily);

    console.log(
      `🧮 Technical Indicators - RSI: LTF=${ltfIndicators.rsi?.toFixed(
        2
      )}, HTF=${htfIndicators.rsi?.toFixed(
        2
      )}, Daily=${dailyIndicators.rsi?.toFixed(2)}`
    );

    // Calculate FVGs
    const ltfFvgs = calculateFairValueGaps(ohlcvData.ltf);
    const htfFvgs = calculateFairValueGaps(ohlcvData.htf);
    const dailyFvgs = calculateFairValueGaps(ohlcvData.daily);

    console.log(
      `📊 Fair Value Gaps - LTF: ${ltfFvgs.length}, HTF: ${htfFvgs.length}, Daily: ${dailyFvgs.length}`
    );

    // Calculate market structure
    const ltfMarketStructure = calculateMarketStructure(ohlcvData.ltf);
    const htfMarketStructure = calculateMarketStructure(ohlcvData.htf);
    const dailyMarketStructure = calculateMarketStructure(ohlcvData.daily);

    console.log(
      `🏗️ Market Structure - LTF recent high/low: ${ltfMarketStructure.recent_high?.toFixed(
        4
      )}/${ltfMarketStructure.recent_low?.toFixed(4)}`
    );

    // Calculate volume analytics
    const ltfVolumeAnalytics = calculateVolumeAnalytics(ohlcvData.ltf);
    const htfVolumeAnalytics = calculateVolumeAnalytics(ohlcvData.htf);
    const dailyVolumeAnalytics = calculateVolumeAnalytics(ohlcvData.daily);

    console.log(
      `📊 Volume Analytics - LTF trend: ${ltfVolumeAnalytics.volume_trend}`
    );

    // Calculate candlestick patterns
    const ltfCandlestickPatterns = calculateCandlestickPatterns(ohlcvData.ltf);
    const htfCandlestickPatterns = calculateCandlestickPatterns(ohlcvData.htf);
    const dailyCandlestickPatterns = calculateCandlestickPatterns(
      ohlcvData.daily
    );

    console.log(
      `🕯️ Candlestick Patterns - LTF: ${ltfCandlestickPatterns.length}, HTF: ${htfCandlestickPatterns.length}, Daily: ${dailyCandlestickPatterns.length}`
    );

    // Build the payload that would be sent to Gemini
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
        candlestick_patterns: ltfCandlestickPatterns.slice(-3), // Last 3 patterns for brevity
      },
      htf: {
        ...htfIndicators,
        fvgs: htfFvgs,
        market_structure: htfMarketStructure,
        volume_analytics: htfVolumeAnalytics,
        candlestick_patterns: htfCandlestickPatterns.slice(-3),
      },
      daily: {
        ...dailyIndicators,
        fvgs: dailyFvgs,
        market_structure: dailyMarketStructure,
        volume_analytics: dailyVolumeAnalytics,
        candlestick_patterns: dailyCandlestickPatterns.slice(-3),
      },
      current_session: getCurrentSession(),
    };

    console.log(
      `📋 Gemini payload size: ${
        JSON.stringify(analysisPayload).length
      } characters`
    );
    console.log(`🔧 Gemini payload data points:`, {
      ltfCandles: ohlcvData.ltf.length,
      htfCandles: ohlcvData.htf.length,
      dailyCandles: ohlcvData.daily.length,
      ltfFvgs: ltfFvgs.length,
      htfFvgs: htfFvgs.length,
      dailyFvgs: dailyFvgs.length,
    });

    return NextResponse.json({
      success: true,
      allCalculatedData: {
        marketData,
        ohlcvData: {
          ltf: ohlcvData.ltf.slice(-10), // Increased to 10 candles for better analysis
          htf: ohlcvData.htf.slice(-10),
          daily: ohlcvData.daily.slice(-10),
        },
        indicators: {
          ltf: ltfIndicators,
          htf: htfIndicators,
          daily: dailyIndicators,
        },
        fvgs: {
          ltf: ltfFvgs,
          htf: htfFvgs,
          daily: dailyFvgs,
        },
        marketStructure: {
          ltf: ltfMarketStructure,
          htf: htfMarketStructure,
          daily: dailyMarketStructure,
        },
        volumeAnalytics: {
          ltf: ltfVolumeAnalytics,
          htf: htfVolumeAnalytics,
          daily: dailyVolumeAnalytics,
        },
        session: getCurrentSession(),
      },
      geminiPayload: analysisPayload,
    });
  } catch (error) {
    console.error("Error in data comparison:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
