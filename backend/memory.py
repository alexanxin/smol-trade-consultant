import json
import numpy as np
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

class MemoryManager:
    def __init__(self, collection_name: str = "market_experiences"):
        # Initialize in-memory Qdrant for testing (no persistence, no locking issues)
        # For production, use path="./qdrant_db" for persistence
        self.client = QdrantClient(":memory:")
        self.collection_name = collection_name
        self.vector_size = 10 # Dimension of our manual feature vector
        
        # Create collection if not exists
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def _vectorize(self, market_data: Dict[str, Any]) -> List[float]:
        """
        Converts market data into a feature vector.
        Features:
        1. RSI (Normalized 0-1)
        2. 1h Change (Capped -10% to +10%, Normalized)
        3. 24h Change (Capped -20% to +20%, Normalized)
        4. Volume vs Avg (Normalized)
        5. Liquidity (Log Normalized)
        6. Bullish FVGs Count (Normalized)
        7. Bearish FVGs Count (Normalized)
        8. Bullish OBs Count (Normalized)
        9. Bearish OBs Count (Normalized)
        10. Sentiment Score (Normalized 0-1)
        """
        try:
            # Extract metrics with defaults
            tech = market_data.get("technical_analysis", {}).get("ltf", {})
            rsi = tech.get("rsi", 50)
            
            # Changes (handling missing data)
            # Note: market_data structure might vary, we need to be robust
            # Based on TraderAgent.analyze_market structure:
            # market_data is the raw API response, tech analysis is separate.
            # We assume the input 'market_data' here is the COMBINED analysis result.
            
            # Let's verify the structure passed to this method.
            # It should be the full 'analysis_result' dict.
            
            # 1. RSI
            rsi_norm = rsi / 100.0
            
            # 2. 1h Change (approximate from raw data if not in tech)
            # We'll use placeholders if not readily available in the dict passed
            # Ideally we pass the 'summary' or specific fields.
            # Let's assume we extract from the raw market_data part if available
            raw = market_data.get("market_data", {})
            p1h = raw.get("price_change_1h_pct", 0) or 0 # Need to ensure this exists
            p1h_norm = np.clip(p1h, -10, 10) / 20.0 + 0.5
            
            # 3. 24h Change
            p24h = raw.get("v24hChangePercent", 0) or 0
            p24h_norm = np.clip(p24h, -20, 20) / 40.0 + 0.5
            
            # 4. Volume (Log scale)
            vol = raw.get("v24hUSD", 0) or 0
            vol_norm = np.log1p(vol) / 20.0 # Approx max log for crypto volumes
            vol_norm = np.clip(vol_norm, 0, 1)
            
            # 5. Liquidity
            liq = raw.get("liquidity", 0) or 0
            liq_norm = np.log1p(liq) / 20.0
            liq_norm = np.clip(liq_norm, 0, 1)
            
            # 6-9. SMC Features
            fvgs = tech.get("fvgs", [])
            bull_fvgs = len([f for f in fvgs if f['type'] == 'bullish'])
            bear_fvgs = len([f for f in fvgs if f['type'] == 'bearish'])
            
            obs = tech.get("order_blocks", [])
            bull_obs = len([o for o in obs if o['type'] == 'bullish'])
            bear_obs = len([o for o in obs if o['type'] == 'bearish'])
            
            # Normalize counts (cap at 10)
            bfvg_norm = min(bull_fvgs, 10) / 10.0
            brfvg_norm = min(bear_fvgs, 10) / 10.0
            bob_norm = min(bull_obs, 10) / 10.0
            brob_norm = min(bear_obs, 10) / 10.0
            
            # 10. Sentiment (Placeholder)
            sent = 0.5 # Neutral
            
            vector = [
                rsi_norm, p1h_norm, p24h_norm, vol_norm, liq_norm,
                bfvg_norm, brfvg_norm, bob_norm, brob_norm, sent
            ]
            
            # Ensure no NaNs
            return [float(x) if not np.isnan(x) else 0.0 for x in vector]
            
        except Exception as e:
            print(f"[Memory] Vectorization error: {e}")
            return [0.0] * self.vector_size

    def store_experience(self, analysis_result: Dict, decision: Dict, outcome: float = 0.0):
        """
        Stores a trading experience.
        Outcome: +1.0 (Win), -1.0 (Loss), 0.0 (Neutral/Unknown)
        """
        vector = self._vectorize(analysis_result)
        
        payload = {
            "token": analysis_result.get("market_data", {}).get("symbol", "UNKNOWN"),
            "action": decision.get("action"),
            "confidence": decision.get("confidence"),
            "outcome": outcome,
            "timestamp": "TODO_ADD_TIMESTAMP"
        }
        
        # Use a random ID or hash
        import uuid
        point_id = str(uuid.uuid4())
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )
        print(f"[Memory] Stored experience {point_id}")

    def retrieve_similar_experiences(self, analysis_result: Dict, limit: int = 5) -> List[Dict]:
        """
        Retrieves similar past experiences.
        """
        print("[Memory] Vectorizing for retrieval...", flush=True)
        vector = self._vectorize(analysis_result)
        print(f"[Memory] Vector created (len={len(vector)}). Searching Qdrant...", flush=True)
        
        try:
            from qdrant_client.models import NamedVector
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit
            )
            print(f"[Memory] Search complete. Found {len(search_result.points)} results.", flush=True)
        except Exception as e:
            print(f"[Memory] Search failed: {e}", flush=True)
            return []
        
        results = []
        for point in search_result.points:
            results.append({
                "score": point.score,
                "payload": point.payload
            })
            
        return results
