from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import os
from app.models import SectorMembership, Sector
from typing import List

router = APIRouter()

# Load sector membership data - use absolute path from working directory
# When running with uvicorn, cwd is the backend directory
BASE_DIR = Path(os.getcwd())
DATA_PATH = BASE_DIR / "data" / "sector_membership.json"


def load_sector_data() -> SectorMembership:
    """Load sector membership data from JSON file"""
    try:
        if not DATA_PATH.exists():
            raise FileNotFoundError(f"Data file not found at {DATA_PATH}")
        
        with open(DATA_PATH, 'r') as f:
            data = json.load(f)
        return SectorMembership(**data)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Sector membership data not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading sector data: {str(e)}")


@router.get("/sectors/membership", response_model=SectorMembership)
async def get_sector_membership():
    """
    Get complete sector membership data
    
    Returns all NIFTY sector indices with their constituent stocks,
    including sector metadata, index symbols, and member weights.
    """
    return load_sector_data()


@router.get("/sectors/{sector_id}/members", response_model=Sector)
async def get_sector_members(sector_id: str):
    """
    Get members of a specific sector
    
    - **sector_id**: Sector identifier (e.g., nifty_bank, nifty_it)
    
    Returns the sector details including all member stocks with weights.
    """
    data = load_sector_data()
    
    # Find the sector
    sector = next((s for s in data.sectors if s.sector_id == sector_id), None)
    
    if not sector:
        available_sectors = [s.sector_id for s in data.sectors]
        raise HTTPException(
            status_code=404, 
            detail=f"Sector '{sector_id}' not found. Available sectors: {', '.join(available_sectors)}"
        )
    
    return sector


@router.get("/sectors", response_model=List[str])
async def list_sectors():
    """
    List all available sector IDs
    
    Returns a list of sector identifiers that can be used with other endpoints.
    """
    data = load_sector_data()
    return [s.sector_id for s in data.sectors]
