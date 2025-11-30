from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
import operator
import asyncio
from .state_manager import GlobalState
from .agents import TechnicalAnalyst, SentimentAnalyst, MasterTrader
from .debate_room import DebateRoom
from .memory import MemoryManager
from .risk_math import RiskEngine

# Define the state dict for LangGraph
class AgentState(TypedDict):
    global_state: GlobalState
    messages: Annotated[list, operator.add]
    current_step: str

class Orchestrator:
    def __init__(self, state_manager: GlobalState, execution_mode: str = None, dry_run: bool = True, token: str = "SOL"):
        self.state = state_manager
        self.execution_mode = execution_mode
        self.dry_run = dry_run
        self.token = token
        self.graph = self._build_graph()
        self.app = self.graph.compile()

    def _build_graph(self):
        # Initialize Graph
        workflow = StateGraph(AgentState)

        # Define Nodes
        workflow.add_node("market_scan", self._market_scan_node)
        workflow.add_node("strategy_analysis", self._strategy_analysis_node)
        workflow.add_node("execution", self._execution_node)

        # Define Edges
        workflow.set_entry_point("market_scan")
        workflow.add_edge("market_scan", "strategy_analysis")
        workflow.add_edge("strategy_analysis", "execution")
        workflow.add_edge("execution", END)

        return workflow

    # Node Implementations
    async def _market_scan_node(self, state: AgentState):
        print("--- Node: Market Scan ---", flush=True)
        
        # Initialize Agents & Memory
        print("Initializing TechnicalAnalyst...", flush=True)
        tech_analyst = TechnicalAnalyst()
        print("Initializing SentimentAnalyst...", flush=True)
        sentiment_analyst = SentimentAnalyst()
        
        memory = MemoryManager()
        
        # Define the token to analyze
        token = self.token
        chain = "solana"
        
        # Run analysis in parallel
        print("Starting analysis tasks...", flush=True)
        tech_task = tech_analyst.analyze(token, chain)
        sentiment_task = sentiment_analyst.analyze(token)
        
        print("Awaiting analysis results...", flush=True)
        try:
            tech_result, sentiment_result = await asyncio.gather(tech_task, sentiment_task)
            print("Analysis complete.", flush=True)
        except Exception as e:
            print(f"ERROR in analysis: {e}", flush=True)
            raise
        
        # Retrieve Memory
        print("Retrieving historical context...", flush=True)
        # We pass the full tech_result which contains raw_data
        similar_experiences = memory.retrieve_similar_experiences(tech_result["raw_data"])
        
        memory_context = "NO SIMILAR PAST SITUATIONS FOUND."
        if similar_experiences:
            memory_context = f"FOUND {len(similar_experiences)} SIMILAR PAST SITUATIONS:\n"
            for exp in similar_experiences:
                payload = exp['payload']
                memory_context += f"- Action: {payload.get('action')}, Outcome: {payload.get('outcome')} (Score: {exp['score']:.2f})\n"
        
        # Get current price from market data
        market_data = tech_result.get("market_data", {})
        current_price = market_data.get('value', 'N/A')
        liquidity = market_data.get('liquidity', 'N/A')
        volume_24h = market_data.get('v24h', market_data.get('volume', 'N/A'))

        # Update state with results
        scan_summary = f"""
        MARKET DATA FOR {token}:

        CURRENT PRICE: ${current_price}
        24H VOLUME: ${volume_24h}
        LIQUIDITY: ${liquidity}

        TECHNICAL SUMMARY:
        {tech_result['summary']}

        SENTIMENT SUMMARY:
        {sentiment_result['summary']}

        HISTORICAL CONTEXT (MEMORY):
        {memory_context}
        """
        
        # Store raw data in state for later use (simplification: attaching to state dict if we modified TypedDict, 
        # but for now we just keep it in the message or we can hack it into the message list as a dict if needed, 
        # but better to just re-fetch or assume agents have it. 
        # Actually, let's pass the raw_data via a special message or just rely on the summary for the debate.)
        
        # We need to pass raw_data to execution node for storage. 
        # Let's append it as a JSON string message or similar.
        import json
        state_update = {
            "messages": [scan_summary, json.dumps(tech_result["raw_data"], default=str)], # Hack: passing raw data as 2nd message
            "current_step": "market_scan"
        }
        return state_update

    async def _strategy_analysis_node(self, state: AgentState):
        print("--- Node: Strategy Analysis (Debate) ---", flush=True)
        
        # Get the context from the previous step (first message)
        context = state["messages"][-2] # The summary is now second to last because we added raw data
        
        # Initialize Debate Room
        debate_room = DebateRoom()
        
        # Run Debate
        transcript = await debate_room.conduct_debate(context)
        
        return {
            "messages": [f"DEBATE TRANSCRIPT:\n{transcript}"],
            "current_step": "strategy_analysis"
        }

    async def _execution_node(self, state: AgentState):
        print("--- Node: Execution (Decision) ---", flush=True)
        
        transcript = state["messages"][-1]
        # Retrieve raw data from earlier message
        import json
        try:
            raw_data = json.loads(state["messages"][1])
        except:
            print("Warning: Could not retrieve raw data for memory storage.")
            raw_data = {}

        # Initialize Components
        master_trader = MasterTrader()
        risk_engine = RiskEngine()
        memory = MemoryManager()
        
        # Make Decision
        decision = await master_trader.make_decision(transcript)
        
        # Calculate Position Size
        similar_exps = memory.retrieve_similar_experiences(raw_data)
        confidence = decision.get('confidence', 50)
        
        position_size = risk_engine.adaptive_sizing(confidence, similar_exps)
        
        # Update Plan
        if decision.get('plan'):
            decision['plan']['position_size_pct'] = position_size
            
        # Store Experience (Simulation: Assume we took the trade and result is unknown/neutral for now)
        memory.store_experience(raw_data, decision, outcome=0.0)
        
        print("\n========================================")
        print("       MASTER TRADER DECISION")
        print("========================================")
        print(f"ACTION: {decision.get('action')}")
        print(f"CONFIDENCE: {decision.get('confidence')}")
        print(f"REASONING: {decision.get('reasoning')}")
        print(f"PLAN: {decision.get('plan')}")
        print(f"KELLY SIZE: {position_size*100:.2f}%")
        print("========================================\n", flush=True)
        
        # Execute if mode is enabled
        if self.execution_mode:
            print(f"[DEBUG] Execution mode enabled: {self.execution_mode}", flush=True)
            from .execution import ExecutionEngine
            
            print(f"[DEBUG] ExecutionEngine imported", flush=True)
            engine = ExecutionEngine(mode=self.execution_mode, dry_run=self.dry_run)
            
            # Get token from orchestrator instance
            token = self.token
            
            print(f"[DEBUG] Calling execute_decision...", flush=True)
            result = engine.execute_decision(decision, token)
            
            print("\n========================================", flush=True)
            print("       EXECUTION RESULT", flush=True)
            print("========================================", flush=True)
            if "signature" in result:
                print(f"✅ SUCCESS: {result['signature']}", flush=True)
            elif "error" in result:
                print(f"❌ ERROR: {result['error']}", flush=True)
            elif "status" in result:
                print(f"ℹ️  STATUS: {result['status']}", flush=True)
            print("========================================\n", flush=True)
        
        return {"current_step": "execution"}

    async def run_cycle(self):
        print("Starting Orchestration Cycle...")
        initial_state = AgentState(
            global_state=self.state.state,
            messages=[],
            current_step="start"
        )
        
        # Run the graph
        async for output in self.app.astream(initial_state):
            for key, value in output.items():
                print(f"Finished step: {key}")
