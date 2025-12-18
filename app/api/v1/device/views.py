from fastapi import APIRouter

from app.utils.standard_response import standard_response

router = APIRouter()


@router.get("/{device_id}")
async def check_device_invite_status(device_id: str):
    """
    Check Device Invite Status
    """
    return standard_response(
        message="Device invite checked",
        data={"device_id": device_id, "status": "invited"}
    )


@router.post("/invite")
async def invite_device_using_coupon():
    """
    Invite Device Using Coupon
    """
    return standard_response(
        message="Device invited",
        data={"status": "success"}
    )
