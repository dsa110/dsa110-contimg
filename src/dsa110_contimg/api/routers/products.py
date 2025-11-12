"""Products-related API routes extracted from routes.py."""

from __future__ import annotations

from fastapi import APIRouter, Request

from dsa110_contimg.api.data_access import fetch_recent_products
from dsa110_contimg.api.models import ProductList

router = APIRouter()


@router.get("/products", response_model=ProductList)
def products(request: Request, limit: int = 50) -> ProductList:
    cfg = request.app.state.cfg
    items = fetch_recent_products(cfg.products_db, limit=limit)
    return ProductList(items=items)
