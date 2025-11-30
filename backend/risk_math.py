class RiskEngine:
    def __init__(self):
        self.max_allocation = 0.20 # Max 20% of bankroll per trade
        self.base_kelly_fraction = 0.5 # Half-Kelly for safety

    def calculate_kelly_size(self, win_rate: float, risk_reward_ratio: float) -> float:
        """
        Calculates the Kelly Criterion percentage.
        K = W - (1-W)/R
        """
        if risk_reward_ratio <= 0:
            return 0.0
            
        kelly_pct = win_rate - (1 - win_rate) / risk_reward_ratio
        return max(0.0, kelly_pct)

    def adaptive_sizing(self, confidence_score: float, similar_outcomes: list) -> float:
        """
        Calculates position size based on confidence and historical outcomes.
        """
        # 1. Determine Win Rate from History (Memory)
        if similar_outcomes:
            wins = len([x for x in similar_outcomes if x['payload'].get('outcome', 0) > 0])
            total = len(similar_outcomes)
            historical_win_rate = wins / total if total > 0 else 0.5
        else:
            historical_win_rate = 0.5 # Default neutral assumption
            
        # 2. Blend with Confidence Score (Master Trader's intuition)
        # Confidence 0-100 -> 0.0-1.0
        # We give 50% weight to history, 50% to current confidence
        model_confidence = confidence_score / 100.0
        estimated_win_rate = (historical_win_rate * 0.5) + (model_confidence * 0.5)
        
        # 3. Assume standard Risk/Reward (e.g., 2:1) if not dynamic
        # In a real system, we'd pull R:R from the trade plan
        risk_reward = 2.0 
        
        # 4. Calculate Kelly
        raw_kelly = self.calculate_kelly_size(estimated_win_rate, risk_reward)
        
        # 5. Apply Safety Multipliers
        safe_kelly = raw_kelly * self.base_kelly_fraction
        
        # 6. Cap at Max Allocation
        final_size = min(safe_kelly, self.max_allocation)
        
        return round(final_size, 4)
