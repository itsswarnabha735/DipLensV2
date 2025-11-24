import unittest
from unittest.mock import MagicMock
from app.scoring_engine import ScoringEngine
from app.state_machine import SectorStateMachine, SectorState
from datetime import datetime, timezone

class TestDeterminism(unittest.TestCase):
    def setUp(self):
        self.scoring_engine = ScoringEngine()
        self.state_machine = SectorStateMachine()
        
    def test_scoring_determinism(self):
        """Test that scoring is deterministic for identical inputs"""
        symbol = "TEST.NS"
        current_price = 100.0
        indicators = {
            "sma_200": 100.0,
            "rsi_14": 50.0,
            "macd_line": 0.0,
            "macd_signal": 0.0,
            "upper_band": 110.0,
            "lower_band": 90.0,
            "volume_avg": 1000000
        }
        dip_analysis = {
            "dip_pct": 10.0,
            "dip_class": "B",
            "days_from_high": 30
        }
        market_data = {
            "current_volume": 1000000,
            "volume_avg": 1000000
        }
        
        # Run 1
        score1 = self.scoring_engine.calculate_pre_score(symbol, current_price, indicators, dip_analysis, market_data)
        
        # Run 2
        score2 = self.scoring_engine.calculate_pre_score(symbol, current_price, indicators, dip_analysis, market_data)
        
        self.assertEqual(score1.pre_score, score2.pre_score)
        self.assertEqual(score1.reasons, score2.reasons)
        
    def test_state_machine_determinism(self):
        """Test that state transitions are deterministic"""
        sector_id = "test_sector"
        
        # Scenario: Deep dip
        snapshot = {
            "sector_id": sector_id,
            "avg_dip": 15.0, # Deep dip
            "breadth_pct": 80.0, # High breadth
            "advancers": 10,
            "decliners": 40,
            "neutral": 0,
            "total": 50,
            "avg_rsi": 30.0,
            "avg_pe": 20.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Run 1
        sm1 = SectorStateMachine()
        sm1.update_state(sector_id, snapshot)
        state1 = sm1.get_current_state(sector_id)
        
        # Run 2
        sm2 = SectorStateMachine()
        sm2.update_state(sector_id, snapshot)
        state2 = sm2.get_current_state(sector_id)
        
        self.assertEqual(state1, state2)

if __name__ == '__main__':
    unittest.main()
