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
            from .position_manager import PositionManager
            
            print(f"[DEBUG] ExecutionEngine imported", flush=True)
            engine = ExecutionEngine(mode=self.execution_mode, dry_run=self.dry_run)
            position_manager = PositionManager()
            
            # Get token from orchestrator instance
            token = self.token
            action = decision.get('action')
            
            # Check if we should execute SELL
            if action == 'SELL':
                open_positions = position_manager.get_all_positions()
                if not open_positions:
                    print("\n========================================", flush=True)
                    print("       EXECUTION SKIPPED", flush=True)
                    print("========================================", flush=True)
                    print("⚠️  SELL signal ignored - No open position to sell", flush=True)
                    print("ℹ️  Waiting for BUY opportunity...", flush=True)
                    print("========================================\n", flush=True)
                    return {"current_step": "execution", "skipped": True}
            
            # Execute based on action type
            # BUY: Check portfolio risk first, then execute
            if action == 'BUY':
                # Initialize Portfolio Manager
                from .portfolio_manager import PortfolioManager
                portfolio_manager = PortfolioManager()
                
                # Get current state
                open_positions = position_manager.get_all_positions()
                cash_balance = await engine.get_cash_balance()
                
                # Update Portfolio Manager
                portfolio_manager.update_state(cash_balance, open_positions)
                
                # Calculate estimated trade value
                plan = decision.get('plan', {})
                entry_price = plan.get('entry', 0)
                size_pct = plan.get('position_size_pct', 0.1)
                
                # Estimate trade value (Size % of Equity)
                estimated_trade_value = size_pct * cash_balance
                
                # Check Risk
                if not portfolio_manager.check_trade_risk(estimated_trade_value):
                    print("\n========================================", flush=True)
                    print("       RISK CHECK FAILED", flush=True)
                    print("========================================", flush=True)
                    print(f"⚠️  Trade rejected by Portfolio Manager (Risk Limit Exceeded)", flush=True)
                    print("========================================\n", flush=True)
                    return {"current_step": "execution", "skipped": True, "reason": "risk_limit"}
                
                print("[Orchestrator] Portfolio Risk Check: PASSED", flush=True)

                # Proceed with execution
                print(f"[DEBUG] Calling execute_decision...", flush=True)
                result = await engine.execute_decision(decision, token)
                
                print("\n========================================", flush=True)
                print("       EXECUTION RESULT", flush=True)
                print("========================================", flush=True)
                
                # Check if execution was successful (live or dry-run)
                execution_success = "signature" in result or (result.get("status") == "simulated" and decision.get('action') == 'BUY')
                
                if "signature" in result:
                    print(f"✅ SUCCESS: {result['signature']}", flush=True)
                elif "error" in result:
                    print(f"❌ ERROR: {result['error']}", flush=True)
                elif "status" in result:
                    print(f"ℹ️  STATUS: {result['status']}", flush=True)
                
                # Record position if this was a successful BUY
                if execution_success:
                    print(f"[DEBUG] Recording position in database...", flush=True)
                    token_address = result.get('token_address', 'SOL_ADDRESS_PLACEHOLDER')
                    if 'amount' not in result:
                        result['amount'] = 1.0
                    position_manager.add_position(decision, result, token, token_address)
            
            # Handle SELL/HOLD
            else:
                print(f"[DEBUG] Calling execute_decision...", flush=True)
                result = await engine.execute_decision(decision, token)
                
                print("\n========================================", flush=True)
                print("       EXECUTION RESULT", flush=True)
                print("========================================", flush=True)
                
                if "signature" in result:
                    print(f"✅ SUCCESS: {result['signature']}", flush=True)
                    
                    # Close position in database if this was a SELL
                    if action == 'SELL':
                        print(f"[DEBUG] Closing position in database...", flush=True)
                        open_positions = position_manager.get_all_positions()
                        
                        # Close all open positions for this token
                        for pos in open_positions:
                            if pos.symbol == token:
                                # Get exit price from result or use current price
                                exit_price = result.get('exit_price', pos.current_price or pos.entry_price)
                                position_manager.close_position(
                                    pos.trade_id,
                                    exit_price,
                                    "MANUAL_SELL"
                                )
                                print(f"[PositionManager] Closed position {pos.trade_id} at ${exit_price:.4f}", flush=True)
                        
                elif "error" in result:
                    print(f"❌ ERROR: {result['error']}", flush=True)
                    
                    # If SELL failed due to insufficient balance, close positions anyway
                    # (This means the token was already sold previously)
                    if action == 'SELL' and "Insufficient" in result.get('error', ''):
                        print(f"[DEBUG] SELL failed due to insufficient balance - closing stale positions...", flush=True)
                        open_positions = position_manager.get_all_positions()
                        
                        for pos in open_positions:
                            if pos.symbol == token:
                                # Use current price or entry price as exit
                                exit_price = pos.current_price or pos.entry_price
                                position_manager.close_position(
                                    pos.trade_id,
                                    exit_price,
                                    "ALREADY_SOLD"
                                )
                                print(f"[PositionManager] Closed stale position {pos.trade_id} (already sold)", flush=True)
                        
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
        
        final_state = None
        # Run the graph
        async for output in self.app.astream(initial_state):
            for key, value in output.items():
                print(f"Finished step: {key}")
                # Update final state with the latest output
                # The output from langgraph is usually a dict with the node name as key and the state update as value
                # We want to capture the accumulated state
                if isinstance(value, dict) and 'global_state' in value:
                    final_state = value['global_state']
                elif isinstance(value, dict):
                     # Sometimes it returns just the update, so we might need to merge or just rely on self.state.state
                     pass
        
        # Since self.state.state is updated throughout the process (via StateManager), 
        # we can just return the latest state from StateManager
        return self.state.state
