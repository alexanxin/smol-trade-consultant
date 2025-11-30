from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class PortfolioState(BaseModel):
    balance_sol: float = 0.0
    positions: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

class MarketContext(BaseModel):
    regime: str = "unknown"  # bull, bear, crab, unknown
    volatility_index: float = 0.0
    dominant_trend: str = "neutral"

class Signal(BaseModel):
    id: str
    symbol: str
    type: str  # BUY, SELL
    confidence: float
    timestamp: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GlobalState(BaseModel):
    portfolio: PortfolioState = Field(default_factory=PortfolioState)
    market_context: MarketContext = Field(default_factory=MarketContext)
    active_signals: List[Signal] = Field(default_factory=list)
    execution_queue: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True

class StateManager:
    def __init__(self):
        self._state = GlobalState()
    
    @property
    def state(self) -> GlobalState:
        return self._state
    
    def update_portfolio(self, balance: float, positions: Dict[str, Any]):
        self._state.portfolio.balance_sol = balance
        self._state.portfolio.positions = positions
        self._state.portfolio.last_updated = datetime.now()
        
    def update_market_context(self, regime: str, volatility: float):
        self._state.market_context.regime = regime
        self._state.market_context.volatility_index = volatility
        
    def add_signal(self, signal: Signal):
        self._state.active_signals.append(signal)
        
    def clear_signals(self):
        self._state.active_signals = []
