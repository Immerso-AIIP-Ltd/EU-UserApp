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
        INSERT INTO user_app.invite_device (device_id, coupon_id)
        VALUES (:device_id, :coupon_id, NOW())
        ON CONFLICT (device_id)
        DO UPDATE SET
            coupon_id = EXCLUDED.coupon_id,
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
    CHECK_USER_EXISTS = text(
        """
        SELECT id
        FROM user_app.user
        WHERE 
            (CAST(:email AS VARCHAR) IS NOT NULL AND email = :email)
            OR
            (CAST(:mobile AS VARCHAR) IS NOT NULL AND mobile = :mobile AND calling_code = :calling_code)
        LIMIT 1;
        """,
    )

    GET_USERNAME_BY_EMAIL = text(
        """
        SELECT up.firstname 
        FROM user_app.user u
        JOIN user_app.user_profile up ON u.id = up.id
        WHERE u.email = :email
        LIMIT 1;
        """,
    )

    REGISTER_WITH_PROFILE = text(
        """
        SELECT * FROM user_app.register_with_profile(
            CAST(:email AS VARCHAR),
            CAST(:mobile AS VARCHAR),
            CAST(:calling_code AS VARCHAR),
            CAST(:password AS VARCHAR),
            CAST(:name AS VARCHAR),
            CAST(:avatar_id AS VARCHAR),
            CAST(:birth_date AS DATE),
            CAST(:profile_image AS VARCHAR)
        );
        """,
    )

    INSERT_USER = text(
        """
        INSERT INTO user_app.user (
            email,
            mobile,
            calling_code,
            password,
            login_type,
            status,
            created_at
        )
        VALUES (
            :email,
            :mobile,
            :calling_code,
            :password,
            :login_type,
            :status,
            NOW()
        )
        RETURNING id;
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
        SELECT
            u.id AS uuid,
            u.email,
            CONCAT(p.firstname, ' ', COALESCE(p.lastname, '')) AS name,
            p.firstname,
            p.lastname,
            u.mobile,
            u.calling_code,
            p.image_url AS image,
            p.country_code AS country,
            p.gender,
            p.about_me,
            TO_CHAR(p.birth_date, 'DD') AS birth_day,
            TO_CHAR(p.birth_date, 'MM') AS birth_month,
            EXTRACT(YEAR FROM p.birth_date)::INTEGER AS birth_year,
            p.avatar_id,
            u.is_password_set,
            p.nick_name,
            TO_CHAR(p.birth_date, 'DD/MM/YYYY') AS birth_date,
            JSONB_BUILD_OBJECT(
                'facebook', (SELECT provider FROM user_app.social_identity_provider WHERE user_id = u.id AND provider = 'facebook' LIMIT 1),
                'apple', (SELECT provider FROM user_app.social_identity_provider WHERE user_id = u.id AND provider = 'apple' LIMIT 1),
                'google', (SELECT provider FROM user_app.social_identity_provider WHERE user_id = u.id AND provider = 'google' LIMIT 1)
            ) AS identity_providers
        FROM user_app.user u
        LEFT JOIN user_app.user_profile p ON u.id = p.id
        WHERE u.id = :user_id;
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