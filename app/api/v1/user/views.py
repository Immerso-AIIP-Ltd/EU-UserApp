from fastapi import APIRouter

from app.utils.standard_response import standard_response

router = APIRouter()


@router.post("/register_with_profile")
async def register_with_profile():
    """
    Sign Up - Step 1 (Check Existence and Register)
    """
    return standard_response(
        message="User registered",
        data={"status": "registered"}
    )


@router.post("/verify_otp_register")
async def verify_otp_register():
    """
    Sign Up - Step 2 (Verify OTP & Create)
    """
    return standard_response(
        message="OTP verified",
        data={"verified": True}
    )


@router.post("/resend_otp")
async def resend_otp():
    """
    Resend OTP (If Expired)
    """
    return standard_response(
        message="OTP resent",
        data={"sent": True}
    )
