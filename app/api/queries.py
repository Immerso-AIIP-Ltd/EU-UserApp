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
        INSERT INTO user_app.invite_device (device_id, coupon_id, created_at)
        VALUES (:device_id, :coupon_id, NOW())
        ON CONFLICT (device_id)
        DO UPDATE SET
            coupon_id = EXCLUDED.coupon_id
        RETURNING device_id
    """,
    )

    CONSUME_COUPON = text(
        """
        UPDATE user_app.invite_coupon
        SET status = 'used',
            consumed_at = NOW()
        WHERE id = :coupon_uuid
        """,
    )

    INVITE_DEVICE_WITH_COUPON = text(
        """
        SELECT * FROM user_app.invite_device_with_coupon(
            :device_id,
            :coupon_id
        )
        """,
    )

    # ==================== REGISTRATION ====================
    CHECK_USER_EXISTS = text(
        """
        SELECT id
        FROM user_app.user
        WHERE
            (CAST(:email AS VARCHAR) IS NOT NULL AND email = :email)
            OR
            (CAST(:mobile AS VARCHAR) IS NOT NULL AND mobile = :mobile
             AND calling_code = :calling_code)
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
            is_password_set,
            login_type,
            type,
            is_email_verified,
            is_mobile_verified,
            created_at
        )
        VALUES (
            :email,
            :mobile,
            :calling_code,
            :password,
            TRUE,
            :login_type,
            :type,
            CASE WHEN CAST(:login_type AS varchar) = 'email' THEN TRUE ELSE FALSE END,
            CASE WHEN CAST(:login_type AS varchar) = 'mobile' THEN TRUE ELSE FALSE END,
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

    GET_USER_COUNT = text(
        """
        SELECT COUNT(*) FROM user_app.user;
        """,
    )

    INSERT_USER_PROFILE = text(
        """
        INSERT INTO user_app.user_profile (
            id,
            firstname,
            lastname,
            birth_date,
            avatar_id,
            image_url,
            created_at,
            modified_at
        )
        VALUES (
            :user_id,
            :firstname,
            :lastname,
            :birth_date,
            :avatar_id,
            :image_url,
            NOW(),
            NOW()
        );
        """,
    )

    INSERT_OTP_VERIFICATION = text(
        """
        INSERT INTO user_app.otp_verification (
            id,
            email,
            mobile,
            calling_code,
            created_at,
            modified_at
        )
        VALUES (
            :user_id,
            :email,
            :mobile,
            :calling_code,
            NOW(),
            NOW()
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
    GET_USER_FOR_LOGIN = text(
        """
        SELECT
            u.id,
            u.email,
            u.mobile,
            u.calling_code,
            u.password,
            u.state,
            u.is_password_set,
            u.failed_login_attempts,
            u.account_locked_until,
            p.firstname || ' ' || COALESCE(p.lastname, '') AS name,
            p.image_url AS image
        FROM user_app.user u
        LEFT JOIN user_app.user_profile p ON u.id = p.id
        WHERE (u.email = :email AND :email IS NOT NULL)
           OR (u.mobile = :mobile AND u.calling_code = :calling_code
               AND :mobile IS NOT NULL);
        """,
    )

    RECORD_LOGIN_SUCCESS = text(
        """
        UPDATE user_app.user
        SET
            failed_login_attempts = 0,
            account_locked_until = NULL,
            last_login_at = NOW(),
            login_count = login_count + 1
        WHERE id = :user_id;
        """,
    )

    RECORD_LOGIN_FAILURE = text(
        """
        UPDATE user_app.user
        SET
            failed_login_attempts = failed_login_attempts + 1,
            account_locked_until = CASE
                WHEN failed_login_attempts + 1 >= :max_attempts
                THEN NOW() + INTERVAL '1 hour'
                ELSE NULL
            END
        WHERE id = :user_id
        RETURNING failed_login_attempts, account_locked_until;
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
                'facebook', (SELECT provider FROM user_app.social_identity_provider
                             WHERE user_id = u.id AND provider = 'facebook' LIMIT 1),
                'apple', (SELECT provider FROM user_app.social_identity_provider
                          WHERE user_id = u.id AND provider = 'apple' LIMIT 1),
                'google', (SELECT provider FROM user_app.social_identity_provider
                           WHERE user_id = u.id AND provider = 'google' LIMIT 1)
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

    INSERT_FRIEND_INVITE = text(
        """
        INSERT INTO user_app.friend_invite (
            inviter_id,
            invited_email,
            invited_mobile,
            invited_calling_code,
            status,
            invite_token,
            invite_sent_at,
            invited_user_id,
            waitlist_id,
            created_at,
            modified_at
        )
        VALUES (
            :inviter_id,
            :invited_email,
            :invited_mobile,
            :invited_calling_code,
            'pending',
            :invite_token,
            NOW(),
            :invited_user_id,
            :waitlist_id,
            NOW(),
            NOW()
        )
        ON CONFLICT (invite_token) DO NOTHING
        RETURNING id;
        """,
    )

    CHECK_FRIEND_INVITE_EXISTS_EMAIL = text(
        """
        SELECT id FROM user_app.friend_invite
        WHERE inviter_id = :inviter_id AND invited_email = :email
        LIMIT 1;
        """,
    )

    CHECK_FRIEND_INVITE_EXISTS_MOBILE = text(
        """
        SELECT id FROM user_app.friend_invite
        WHERE inviter_id = :inviter_id
          AND invited_mobile = :mobile
          AND invited_calling_code = :calling_code
        LIMIT 1;
        """,
    )

    JOIN_WAITLIST = text(
        """
        SELECT * FROM user_app.join_waitlist(
            :device_id,
            :email,
            :mobile,
            :calling_code
        );
        """,
    )

    GET_WAITLIST_BY_DEVICE_AND_EMAIL = text(
        """
        SELECT * FROM user_app.waitlist
        WHERE device_id = :device_id AND email = :email
        LIMIT 1;
        """,
    )

    GET_WAITLIST_BY_EMAIL = text(
        """
        SELECT * FROM user_app.waitlist
        WHERE email = :email
        LIMIT 1;
        """,
    )

    GET_WAITLIST_BY_DEVICE = text(
        """
        SELECT * FROM user_app.waitlist
        WHERE device_id = :device_id
        LIMIT 1;
        """,
    )

    GET_WAITLIST_BY_MOBILE = text(
        """
        SELECT * FROM user_app.waitlist
        WHERE mobile = :mobile AND calling_code = :calling_code
        LIMIT 1;
        """,
    )

    UPDATE_WAITLIST_VERIFIED = text(
        """
        UPDATE user_app.waitlist
        SET is_verified = TRUE, modified_at = NOW()
        WHERE id = :id
        RETURNING id, queue_number;
        """,
    )

    INSERT_WAITLIST_ENTRY = text(
        """
        INSERT INTO user_app.waitlist (
            device_id,
            email,
            mobile,
            calling_code,
            queue_number,
            is_verified,
            created_at,
            modified_at
        )
        VALUES (
            :device_id,
            :email,
            :mobile,
            :calling_code,
            (SELECT COALESCE(MAX(queue_number), 0) + 1 FROM user_app.waitlist),
            FALSE,
            NOW(),
            NOW()
        )
        RETURNING id, queue_number;
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

    GET_USER_BY_SOCIAL_IDENTITY = text(
        """
        SELECT u.id, u.email, u.mobile, u.calling_code, u.state,
               sip.provider_user_id as social_id
        FROM user_app.user u
        JOIN user_app.social_identity_provider sip ON u.id = sip.user_id
        WHERE sip.provider = :provider AND sip.provider_user_id = :social_id
        LIMIT 1;
        """,
    )

    SIGNUP_WITH_SOCIAL_DATA = text(
        """
        WITH new_user AS (
            INSERT INTO user_app.user (
                email,
                mobile,
                calling_code,
                login_type,
                state,
                is_email_verified,
                created_at,
                modified_at
            )
            VALUES (
                CAST(:email AS VARCHAR),
                '',
                '',
                :provider,
                'active',
                TRUE,
                NOW(),
                NOW()
            )
            RETURNING id, email
        ),
        new_profile AS (
            INSERT INTO user_app.user_profile (
                id,
                firstname,
                country_code,
                created_at,
                modified_at
            )
            SELECT id, CAST(:name AS VARCHAR), CAST(:country AS VARCHAR), NOW(), NOW()
            FROM new_user
        )
        SELECT id, email FROM new_user;
        """,
    )

    UPSERT_SOCIAL_IDENTITY_PROVIDER = text(
        """
        INSERT INTO user_app.social_identity_provider
        (user_id, provider, provider_user_id, token, created_at)
        VALUES (:user_id, :provider, :social_id, :token, NOW())
        ON CONFLICT (user_id, provider) DO UPDATE SET
            provider_user_id = EXCLUDED.provider_user_id,
            token = EXCLUDED.token,
            modified_at = NOW();
        """,
    )

    # ==================== ACCOUNT ====================
    UPDATE_AUTH_SESSION_LOGOUT = text(
        """
        UPDATE user_app.authentication_session
        SET
            is_active = FALSE,
            logged_out_at = NOW(),
            logout_reason = 'user_initiated'
        WHERE user_id = :user_id AND device_id = :device_id AND is_active = TRUE
        """,
    )

    UPDATE_USER_DEACTIVATED = text(
        """
        UPDATE user_app.user
        SET
            state = 'deactivated',
            deactivated_at = NOW(),
            modified_at = NOW()
        WHERE id = :user_id
        """,
    )
    # ==================== AUTHENTICATION ====================
    GET_APP_CONSUMER = text(
        """
        SELECT id, client_id, client_secret, partner_code
        FROM user_app.app_consumer
        WHERE client_id = :client_id
        LIMIT 1;
        """,
    )

    GET_CLIENT_SECRET = text(
        """
        SELECT client_secret
        FROM user_app.app_consumer
        WHERE client_id = :client_id
        LIMIT 1;
        """,
    )

    INSERT_USER_AUTH_TOKEN = text(
        """
        INSERT INTO user_app.user_auth_token (
            uuid,
            token,
            app_consumer_id,
            device_id,
            expires_at,
            partner_id,
            is_active,
            created_at
        )
        VALUES (
            :uuid,
            :token,
            :app_consumer_id,
            :device_id,
            :expires_at,
            :partner_id,
            TRUE,
            NOW()
        );
        """,
    )

    GET_USER_BY_EMAIL = text(
        """
        SELECT id, email, mobile, calling_code, state
        FROM user_app.user
        WHERE email = :email
        """,
    )

    GET_USER_BY_MOBILE = text(
        """
        SELECT id, email, mobile, calling_code, state
        FROM user_app.user
        WHERE mobile = :mobile AND calling_code = :calling_code
        """,
    )
    UPDATE_USER_PASSWORD = text(
        """
        UPDATE user_app.user
        SET password = :password,
            is_password_set = TRUE
        WHERE id = :user_id
        """,
    )

    GET_USER_PASSWORD_HASH = text(
        """
        SELECT password
        FROM user_app.user
        WHERE id = :user_id
        """,
    )

    DEACTIVATE_USER_TOKEN = text(
        """
        UPDATE user_app.user_auth_token
        SET is_active = False
        WHERE token = :token AND device_id = :device_id
        """,
    )

    # ==================== DEVICE MANAGEMENT ====================
    GET_DEVICE_BY_ID = text(
        """
        SELECT * FROM user_app.device WHERE device_id = :device_id LIMIT 1
        """,
    )

    CHECK_DEVICE_EXISTS = text(
        """
        SELECT 1 FROM user_app.device WHERE device_id = :device_id LIMIT 1
        """,
    )

    INSERT_DEVICE = text(
        """
        INSERT INTO user_app.device (
            device_id, user_id, device_name, platform, device_type,
            device_active, user_token, created_at, modified_at
        ) VALUES (
            :device_id, :user_id, :device_name, :platform, :device_type,
            TRUE, :user_token, NOW(), NOW()
        )
        RETURNING device_id
        """,
    )

    UPDATE_DEVICE = text(
        """
        UPDATE user_app.device
        SET
            device_type = COALESCE(:device_type, device_type),
            device_name = COALESCE(:device_name, device_name),
            push_token = COALESCE(:push_token, push_token),
            modified_at = NOW()
        WHERE device_id = :device_id
        """,
    )

    LINK_DEVICE_TO_USER = text(
        """
        UPDATE user_app.device
        SET
            user_id = :user_id,
            user_token = :user_token,
            device_active = TRUE,
            date_deactivated = NULL,
            modified_at = NOW()
        WHERE device_id = :device_id
        """,
    )

    DEACTIVATE_DEVICE = text(
        """
        UPDATE user_app.device
        SET
            device_active = FALSE,
            date_deactivated = NOW(),
            modified_at = NOW()
        WHERE device_id = :device_id AND user_id = :user_id
        """,
    )

    DEACTIVATE_USER_AUTH_TOKEN = text(
        """
        UPDATE user_app.user_auth_token
        SET is_active = FALSE
        WHERE uuid = :user_id AND token = :token
        """,
    )

    GET_ACTIVE_DEVICES_FOR_USER = text(
        """
        SELECT * FROM user_app.device
        WHERE user_id = :user_id AND device_active = TRUE
        """,
    )
