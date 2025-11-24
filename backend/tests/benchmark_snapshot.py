import time
import asyncio
from unittest.mock import patch, MagicMock
from app.models import Bar

# Mock data generator
def generate_mock_bars(count=200):
    bars = []
    for i in range(count):
        bars.append(Bar(
            t=f"2023-01-{i%30+1:02d}T00:00:00Z",
            o=100.0, h=105.0, l=95.0, c=100.0, v=1000000
        ))
    return bars

async def benchmark():
    print("Starting benchmark...")
    
    # Mock yahoo_provider.get_bars_batch
    with patch('app.providers.yahoo.yahoo_provider.get_bars_batch') as mock_batch:
        # Return mock data for 50 symbols
        mock_data = {f"SYM{i}": generate_mock_bars() for i in range(50)}
        mock_batch.return_value = mock_data
        
        # Also mock load_sector_data to return a test sector with 50 members
        with patch('app.routers.sectors.load_sector_data') as mock_load:
            mock_sector = MagicMock()
            mock_sector.sector_id = "BENCH_SECTOR"
            mock_sector.sector_name = "Benchmark Sector"
            mock_sector.members = [MagicMock(symbol=f"SYM{i}", weight_hint=0.02) for i in range(50)]
            mock_load.return_value.sectors = [mock_sector]
            
            start_time = time.time()
            
            from app.routers.sector_snapshots import get_sector_snapshot
            await get_sector_snapshot("BENCH_SECTOR")
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Processed 50 symbols in {duration:.4f} seconds")
            
            if duration < 2.0:
                print("PASS: Performance within limits (<2s)")
            else:
                print("FAIL: Performance too slow (>2s)")

if __name__ == "__main__":
    asyncio.run(benchmark())
