#!/usr/bin/env python3
"""
Sector Membership Validator

Validates all tickers in sector_membership.json against Yahoo Finance
to ensure they are valid and not delisted.

Usage:
    python tools/validate_members.py
"""

import json
import sys
from pathlib import Path
import yfinance as yf
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

DATA_PATH = Path(__file__).parent.parent / "data" / "sector_membership.json"


def load_sector_data():
    """Load sector membership data"""
    with open(DATA_PATH, 'r') as f:
        return json.load(f)


def validate_symbol(symbol: str) -> dict:
    """
    Validate a single symbol with Yahoo Finance
    
    Returns:
        dict with 'valid', 'error', and 'info' keys
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Check if we got valid data
        if not info or 'symbol' not in info:
            return {
                'valid': False,
                'error': 'No data returned',
                'info': None
            }
        
        # Check if delisted/suspended
        quote_type = info.get('quoteType', '')
        if quote_type == 'NONE' or not quote_type:
            return {
                'valid': False,
                'error': 'Possibly delisted or invalid',
                'info': info
            }
        
        return {
            'valid': True,
            'error': None,
            'info': {
                'name': info.get('longName', info.get('shortName', '')),
                'exchange': info.get('exchange', ''),
                'quoteType': quote_type
            }
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'info': None
        }


def validate_all():
    """Validate all symbols in sector membership data"""
    print("=" * 80)
    print("SECTOR MEMBERSHIP VALIDATOR")
    print("=" * 80)
    print(f"Data source: {DATA_PATH}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    print()
    
    data = load_sector_data()
    
    total_symbols = 0
    valid_symbols = 0
    invalid_symbols = []
    
    for sector in data['sectors']:
        sector_name = sector['sector_name']
        sector_id = sector['sector_id']
        members = sector['members']
        
        print(f"\n📊 {sector_name} ({sector_id})")
        print(f"   Index: {sector['index_symbol']}")
        print(f"   Members: {len(members)}")
        print()
        
        for member in members:
            symbol = member['symbol']
            name = member['name']
            total_symbols += 1
            
            print(f"   Validating {symbol}... ", end='')
            result = validate_symbol(symbol)
            
            if result['valid']:
                print(f"✅ OK - {result['info']['name']}")
                valid_symbols += 1
            else:
                print(f"❌ FAILED - {result['error']}")
                invalid_symbols.append({
                    'sector': sector_name,
                    'symbol': symbol,
                    'name': name,
                    'error': result['error']
                })
    
    # Summary
    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total symbols checked: {total_symbols}")
    print(f"Valid symbols: {valid_symbols} ({valid_symbols/total_symbols*100:.1f}%)")
    print(f"Invalid symbols: {len(invalid_symbols)} ({len(invalid_symbols)/total_symbols*100:.1f}%)")
    print()
    
    if invalid_symbols:
        print("❌ INVALID SYMBOLS:")
        print()
        for item in invalid_symbols:
            print(f"   {item['sector']}")
            print(f"     Symbol: {item['symbol']}")
            print(f"     Name: {item['name']}")
            print(f"     Error: {item['error']}")
            print()
    else:
        print("✅ All symbols are valid!")
    
    print("=" * 80)
    
    # Return exit code based on results
    return 0 if len(invalid_symbols) == 0 else 1


if __name__ == "__main__":
    exit_code = validate_all()
    sys.exit(exit_code)
