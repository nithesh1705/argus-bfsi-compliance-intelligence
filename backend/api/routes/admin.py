"""
ARGUS — Admin API Route (backend/api/routes/admin.py)

Endpoints for:
1. Executive Analytics & Dynamic Time-Series Chart Data (/api/admin/analytics)
2. Master Data CRUD:
   - Users: /api/admin/users
   - Relationship Managers: /api/admin/rms
   - Customers: /api/admin/customers
   - Funds / Products: /api/admin/products
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, status
from pydantic import BaseModel

from backend.db.repositories.admin_repo import (
    get_admin_analytics,
    list_users_admin,
    create_user_admin,
    update_user_admin,
    delete_user_admin,
    list_rms_admin,
    create_rm_admin,
    update_rm_admin,
    delete_rm_admin,
    list_customers_admin,
    create_customer_admin,
    update_customer_admin,
    delete_customer_admin,
    list_products_admin,
    create_product_admin,
    update_product_admin,
    delete_product_admin,
    list_authorities_admin,
    create_authority_admin,
    update_authority_admin,
    delete_authority_admin,
)

logger = logging.getLogger("argus.api.admin")

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


# ==============================================================================
# Analytics & Chart Data
# ==============================================================================

@router.get("/analytics", response_model=Dict[str, Any])
def get_analytics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Returns aggregated time-series and categorical chart statistics."""
    try:
        return get_admin_analytics(start_date=start_date, end_date=end_date)
    except Exception as exc:
        logger.exception(f"Failed to fetch admin analytics: {exc}")
        raise HTTPException(status_code=500, detail=f"Analytics calculation error: {str(exc)}")


# ==============================================================================
# Users CRUD
# ==============================================================================

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "Audit Officer"
    team: str = "Compliance"
    access_level: str = "All"
    full_name: Optional[str] = None
    is_active: bool = True

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    team: Optional[str] = None
    access_level: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/users")
def get_users():
    return list_users_admin()

@router.post("/users", status_code=status.HTTP_201_CREATED)
def add_user(req: UserCreateRequest):
    try:
        return create_user_admin(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.put("/users/{user_id}")
def edit_user(user_id: str, req: UserUpdateRequest):
    success = update_user_admin(user_id, req.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="User not found or no fields updated")
    return {"success": True, "message": f"User '{user_id}' updated"}

@router.delete("/users/{user_id}")
def remove_user(user_id: str):
    delete_user_admin(user_id)
    return {"success": True, "message": f"User '{user_id}' deleted"}


# ==============================================================================
# RMs CRUD
# ==============================================================================

class RMCreateRequest(BaseModel):
    rm_id: Optional[str] = None
    full_name: str
    branch: str = "Main Branch"
    joined_date: Optional[str] = None
    active: bool = True

class RMUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    branch: Optional[str] = None
    joined_date: Optional[str] = None
    active: Optional[bool] = None

@router.get("/rms")
def get_rms():
    return list_rms_admin()

@router.post("/rms", status_code=status.HTTP_201_CREATED)
def add_rm(req: RMCreateRequest):
    try:
        return create_rm_admin(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.put("/rms/{rm_id}")
def edit_rm(rm_id: str, req: RMUpdateRequest):
    success = update_rm_admin(rm_id, req.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="RM not found")
    return {"success": True, "message": f"RM '{rm_id}' updated"}

@router.delete("/rms/{rm_id}")
def remove_rm(rm_id: str):
    delete_rm_admin(rm_id)
    return {"success": True, "message": f"RM '{rm_id}' deleted"}


# ==============================================================================
# Customers CRUD
# ==============================================================================

class CustomerCreateRequest(BaseModel):
    customer_id: Optional[str] = None
    full_name: str
    mobile_number: str = "+91 98765 00000"
    risk_profile: str = "Moderate"
    investment_experience: str = "Intermediate"
    kyc_status: str = "VERIFIED"

class CustomerUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    mobile_number: Optional[str] = None
    risk_profile: Optional[str] = None
    investment_experience: Optional[str] = None
    kyc_status: Optional[str] = None

@router.get("/customers")
def get_customers():
    return list_customers_admin()

@router.post("/customers", status_code=status.HTTP_201_CREATED)
def add_customer(req: CustomerCreateRequest):
    try:
        return create_customer_admin(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.put("/customers/{customer_id}")
def edit_customer(customer_id: str, req: CustomerUpdateRequest):
    success = update_customer_admin(customer_id, req.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"success": True, "message": f"Customer '{customer_id}' updated"}

@router.delete("/customers/{customer_id}")
def remove_customer(customer_id: str):
    delete_customer_admin(customer_id)
    return {"success": True, "message": f"Customer '{customer_id}' deleted"}


# ==============================================================================
# Products / Funds CRUD
# ==============================================================================

class ProductCreateRequest(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    risk_class: str = "Moderate Risk"
    suitable_risk_profiles: str = "Moderate, Aggressive"
    disclosure_requirements: str = "Standard SEBI MF Scheme Information Document"

class ProductUpdateRequest(BaseModel):
    product_name: Optional[str] = None
    risk_class: Optional[str] = None
    suitable_risk_profiles: Optional[str] = None
    disclosure_requirements: Optional[str] = None

@router.get("/products")
def get_products():
    return list_products_admin()

@router.post("/products", status_code=status.HTTP_201_CREATED)
def add_product(req: ProductCreateRequest):
    try:
        return create_product_admin(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.put("/products/{product_id}")
def edit_product(product_id: str, req: ProductUpdateRequest):
    success = update_product_admin(product_id, req.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "message": f"Product '{product_id}' updated"}

@router.delete("/products/{product_id}")
def remove_product(product_id: str):
    delete_product_admin(product_id)
    return {"success": True, "message": f"Product '{product_id}' deleted"}


# ==============================================================================
# Regulatory Authorities CRUD (SEBI, AMFI, RBI, etc.)
# ==============================================================================

class AuthorityCreateRequest(BaseModel):
    authority_id: Optional[str] = None
    short_code: str
    name: str
    jurisdiction: Optional[str] = "India"
    website_url: Optional[str] = ""
    description: Optional[str] = ""
    active: bool = True

class AuthorityUpdateRequest(BaseModel):
    name: Optional[str] = None
    short_code: Optional[str] = None
    jurisdiction: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

@router.get("/authorities")
def get_authorities(active_only: bool = Query(False, description="Filter for active authorities only")):
    return list_authorities_admin(active_only=active_only)

@router.post("/authorities", status_code=status.HTTP_201_CREATED)
def add_authority(req: AuthorityCreateRequest):
    try:
        return create_authority_admin(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.put("/authorities/{authority_id}")
def edit_authority(authority_id: str, req: AuthorityUpdateRequest):
    success = update_authority_admin(authority_id, req.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Regulatory Authority not found")
    return {"success": True, "message": f"Regulatory Authority '{authority_id}' updated"}

@router.delete("/authorities/{authority_id}")
def remove_authority(authority_id: str):
    delete_authority_admin(authority_id)
    return {"success": True, "message": f"Regulatory Authority '{authority_id}' deleted"}

