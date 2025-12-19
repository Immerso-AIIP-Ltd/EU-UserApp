from sqlalchemy import text


class UserQueries:
    """Centralized SQL queries for User App API."""

    # ==================== DEVICE INVITE ====================
    CHECK_DEVICE_INVITE_STATUS = text(
        """
        SELECT * FROM user_app.check_device_invite_status(
            :device_id
        );
        """,
    )

    GET_COUPON = text(
        """
    SELECT id,
        status = 'used' AS is_consumed,
        expiry_date < NOW() AS is_expired
    FROM user_app.invite_coupon
    WHERE code = :coupon_id
    """,
    )

    CHECK_DEVICE_INVITED = text(
        """
        SELECT 1
        FROM user_app.invite_device
        WHERE device_id = :device_id
          AND coupon_id IS NOT NULL
    """,
    )

    UPSERT_DEVICE_INVITE = text(
        """
        INSERT INTO user_app.invite_device (device_id, coupon_id, invited_at)
        VALUES (:device_id, :coupon_uuid, NOW())
        ON CONFLICT (device_id)
        DO UPDATE SET
            coupon_id = EXCLUDED.coupon_id,
            invited_at = NOW()
        RETURNING device_id
    """,
    )

    CONSUME_COUPON = text(
        """
        UPDATE user_app.invite_coupon
        SET is_consumed = TRUE,
            consumed_at = NOW()
        WHERE id = :coupon_uuid
        """    
    )

    INVITE_DEVICE_WITH_COUPON = text(
        """
        SELECT * FROM user_app.invite_device_with_coupon(
            :device_id,
            :coupon_id
        )
        """
    )

    # ==================== REGISTRATION ====================
    REGISTER_WITH_PROFILE = text(
        """
        SELECT * FROM user_app.register_with_profile(
            :email,
            :mobile,
            :calling_code,
            :password,
            :name,
            :avatar_id,
            :birth_date,
            :profile_image
        );
        """,
    )

    VERIFY_OTP_REGISTER = text(
        """
        SELECT * FROM user_app.verify_otp_register(
            :email,
            :mobile,
            :calling_code,
            :otp,
            :password,
            :intent
        );
        """,
    )

    RESEND_OTP = text(
        """
        SELECT * FROM user_app.resend_otp(
            :email,
            :mobile,
            :calling_code,
            :intent
        );
        """,
    )

    # ==================== LOGIN ====================
    LOGIN_USER = text(
        """
        SELECT * FROM user_app.login_user(
            :email,
            :mobile,
            :calling_code,
            :password
        );
        """,
    )

    FORGOT_PASSWORD = text(
        """
        SELECT * FROM user_app.forgot_password(
            :email,
            :mobile,
            :calling_code
        );
        """,
    )

    CHANGE_PASSWORD = text(
        """
        SELECT * FROM user_app.change_password(
            :user_id,
            :new_password
        );
        """,
    )

    # ==================== PROFILE ====================
    GET_USER_PROFILE = text(
        """
        SELECT * FROM user_app.get_user_profile(
            :user_id
        );
        """,
    )

    UPDATE_USER_PROFILE = text(
        """
        SELECT * FROM user_app.update_user_profile(
            :user_id,
            :name,
            :gender,
            :about_me,
            :birth_date,
            :nick_name,
            :country,
            :avatar_id,
            :profile_image
        );
        """,
    )

    UPDATE_EMAIL_MOBILE = text(
        """
        SELECT * FROM user_app.update_email_mobile(
            :user_id,
            :email,
            :mobile,
            :calling_code
        );
        """,
    )

    VERIFY_OTP = text(
        """
        SELECT * FROM user_app.verify_otp(
            :email,
            :mobile,
            :calling_code,
            :otp,
            :intent
        );
        """,
    )

    # ==================== SOCIAL / WAITLIST ====================
    SOCIAL_FRIEND_INVITE = text(
        """
        SELECT * FROM user_app.friend_invite(
            :user_id,
            :invited_list
        );
        """,
    )

    JOIN_WAITLIST = text(
        """
        SELECT * FROM user_app.join_waitlist(
            :device_id,
            :email_id,
            :mobile,
            :calling_code
        );
        """,
    )

    WAITLIST_VERIFY_OTP = text(
        """
        SELECT * FROM user_app.waitlist_verify_otp(
            :email,
            :mobile,
            :calling_code,
            :otp,
            :intent
        );
        """,
    )

    SOCIAL_LOGIN = text(
        """
        SELECT * FROM user_app.social_login(
            :provider,
            :user_id,
            :token,
            :device_id
        );
        """,
    )

    # ==================== ACCOUNT ====================
    LOGOUT_USER = text(
        """
        SELECT * FROM user_app.logout_user(
            :user_id,
            :device_id
        );
        """,
    )

    DEACTIVATE_USER = text(
        """
        SELECT * FROM user_app.deactivate_user(
            :user_id
        );
        """,
    )
