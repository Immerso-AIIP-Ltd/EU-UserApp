from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.utils.standard_response import standard_response

router = APIRouter()


@router.post("/register_with_profile")
async def register_with_profile(request: Request) -> JSONResponse:
    """
    Sign Up - Step 1 (Check Existence and Register)
    """
    return standard_response(
        request=request,
        message="User registered",
        data={"status": "registered"},
    )


@router.post("/verify_otp_register")
async def verify_otp_register(request: Request) -> JSONResponse:
    """
    Sign Up - Step 2 (Verify OTP & Create)
    """
    return standard_response(
        request=request,
        message="OTP verified",
        data={"verified": True},
    )


@router.post("/resend_otp")
async def resend_otp(request: Request) -> JSONResponse:
    """
    Resend OTP (If Expired)
    """
    return standard_response(request=request, message="OTP resent", data={"sent": True})
