import { NextResponse } from "next/server";

interface EnhancedAnalysisRequest {
  analysis: string;
  token: string;
  currentPrice: number;
  action: "BUY" | "SELL" | "HOLD";
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  convictionScore: number;
  riskRewardRatio: number;
  prompt: string;
}

export async function POST(request: Request) {
  try {
    const { prompt }: EnhancedAnalysisRequest = await request.json();

    // Use the environment variable for the API key
    const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

    if (!GEMINI_API_KEY) {
      return NextResponse.json(
        { error: "GEMINI_API_KEY not configured in environment" },
        { status: 500 }
      );
    }

    // Call the Gemini API directly from the server
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                {
                  text: prompt,
                },
              ],
            },
          ],
        }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        `Gemini API Error: ${response.status} - ${JSON.stringify(errorData)}`
      );
    }

    const data = await response.json();
    const enhancedAnalysis =
      data.candidates?.[0]?.content?.parts?.[0]?.text ||
      "No analysis generated";

    // Return the enhanced analysis
    return NextResponse.json({
      enhanced_analysis: enhancedAnalysis,
    });
  } catch (error: unknown) {
    console.error("Error enhancing analysis with Gemini:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error occurred";
    return NextResponse.json(
      {
        error: "Failed to enhance analysis with Gemini",
        details: errorMessage,
      },
      { status: 500 }
    );
  }
}
