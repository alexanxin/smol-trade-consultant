import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

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

export async function POST(request: Request) {
  const { token, chain } = await request.json();

  if (!token || !chain) {
    return NextResponse.json(
      { error: "Missing token or chain" },
      { status: 400 }
    );
  }

  try {
    // Call the CLEAN Python trading agent (no ANSI codes, direct JSON)
    const { stdout, stderr } = await execAsync(
      `cd /Users/aleksandar/Desktop/Raboten/trader-agent && python3 frontend/src/lib/trader-agent-clean.py ${token} ${chain}`
    );

    if (stderr) {
      console.warn("Python script stderr:", stderr);
    }

    // Parse the clean JSON output directly - NO complex regex parsing needed!
    const response = JSON.parse(stdout);

    // If there's an error in the response, handle it gracefully
    if (response.error) {
      return NextResponse.json({
        formatted: false,
        error: response.error,
        token: token,
        currentPrice: 0,
        action: "HOLD",
        entryPrice: 0,
        stopLoss: 0,
        takeProfit: 0,
        convictionScore: 0,
        riskRewardRatio: 0,
        reasoning: "Analysis failed",
        timestamp: new Date().toISOString(),
        highProbabilitySetups: [],
        raw: {
          action: "HOLD",
          entry_price: 0,
          stop_loss: 0,
          take_profit: 0,
          conviction_score: 0,
          reasoning: response.error,
        },
      });
    }

    // Return the structured response directly - NO MORE COMPLEX PARSING!
    return NextResponse.json(response);
  } catch (error: unknown) {
    console.error("Error getting signal analysis:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error occurred";
    return NextResponse.json(
      { error: "Failed to get signal analysis", details: errorMessage },
      { status: 500 }
    );
  }
}

// Optional: Add a GET endpoint for testing
export async function GET() {
  return NextResponse.json(
    {
      message: "Trading Analysis API",
      usage: "POST request with { token: 'SOL', chain: 'solana' }",
      available_tokens: ["SOL", "ETH", "BNB"],
      available_chains: ["solana", "ethereum", "bsc", "polygon"],
    },
    { status: 200 }
  );
}
