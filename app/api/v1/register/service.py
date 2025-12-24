from datetime import datetime
import logging
import random
import select
import smtplib
import socket
import time
import traceback
from asyncio.log import logger
from typing import List
import uuid
import pytz

from app.core import exceptions
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from app.api.v1.register import redis
from app.api.v1.register.auth import UserLoginService
from app.api.v1.register.task import get_hashed_password, get_sha1_hash
from app.db.models.user_app import Device, User
import dns.resolver
from app.settings import settings

from app.api.v1.register import deeplinks
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.deeplinks import *
from app.api.v1.register.otp import GenerateOtpService
from app.api.v1.register.redis import *
from app.core.constants import Intent
from app.core.exceptions.exceptions import (
    CommServiceAPICallFailed,
    EmailNotRegistered,
    ForgotPassword,
    MobileInvalid,
    MobileNotRegistered,
)

logger = logging.getLogger("django")

from app.api.queries import UserQueries
from app.db.utils import execute_query

async def get_random_bigint():
    BIGINT_LIMIT = 2**63
    return random.randint(0, BIGINT_LIMIT)

class MobileVerificationService(object):
    @staticmethod
    def mobile_verification_service(mobile, calling_code):
        payload = {
            "mobile_number": mobile,
            "calling_code": calling_code,
        }
        response = call_communication_api(deeplinks.MOBILE_VERIFY_URL, payload)
        if "status" in response and response["status"] == "success":
            if not response["data"]["is_valid"]:
                raise MobileInvalid("Mobile number is not valid.")
        else:
            raise CommServiceAPICallFailed()

class EmailDnsVerifyService(object):
    def __init__(self, email="", show_support_message=False):
        self.show_support_message = show_support_message
        self.email = email
        self.email_domain = self.email.split("@")[1] if "@" in self.email else ""

    def verify(self):
        start_time = time.time()
        try:
            if (not self.email) or (not self.email_domain) or redis.get_val("dns.invalid_domains.{0}".format(self.email_domain)):
                self.raise_exception("Invalid email domain")

            if self.email_domain in redis.smembers("dns.skip_domains_for_verification"):
                return

            if redis.get_val("dns.valid_emails.{0}".format(self.email)):
                return

            cached_exception = redis.get_val("dns.invalid_emails.{0}".format(self.email))
            if cached_exception:
                self.raise_exception(cached_exception)

            self.get_mx_record_for_domain()
            self.verify_smtp_session()
            self.cache_valid_email()
        finally:
            logger.info("Time for EmailDnsVerifyService", extra= {
                "time": "{0} seconds".format(time.time() - start_time),
                "data": self.email,
            })

    def cache_valid_email(self):
        redis.set_val("dns.valid_domains.{0}".format(self.email_domain), "true", settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)
        redis.set_val("dns.valid_emails.{0}".format(self.email), "true", settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)

    def get_mx_record_for_domain(self):
        try:
            # check mx record for email domain
            records = dns.resolver.query(self.email_domain, "MX")
            self.mxRecord = str(records[0].exchange)
            if (not self.mxRecord or self.mxRecord == "."):
                raise dns.resolver.NoAnswer
        except (dns.resolver.NXDOMAIN,
                dns.resolver.NoAnswer,
                dns.resolver.NoMetaqueries,
                dns.resolver.NoNameservers,
                dns.resolver.NoRootSOA,
                dns.resolver.NotAbsolute,
                dns.resolver.YXDOMAIN):
            redis.set_val(
                "dns.invalid_domains.{0}".format(self.email_domain),
                "true",
                settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)
            self.raise_exception("Invalid email domain")
        except Exception as e:
            logger.info("Unhandled exception for domain", extra= {
                "exception": str(e),
                "data": self.email_domain,
            })
            self.raise_exception("Invalid email domain")

    def verify_smtp_session(self):
        retry_count = 0

        while retry_count < 3:
            try:
                smtp = smtplib.SMTP(timeout = 3)
                smtp.connect(self.mxRecord)
                smtp_status = smtp.helo()[0]
                if smtp_status != 250:
                    smtp.quit()
                    self.process_invalid_smtp_response("Email doesn't exist")

                smtp.mail("")
                smtp_status = smtp.rcpt(self.email)[0]
                if smtp_status != 250:
                    smtp.quit()
                    self.process_invalid_smtp_response("Email doesn't exist")

                break
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, ConnectionResetError, socket.error) as exception:
                logger.error(
                    "UNABLE TO CONNECT SMTP SERVER",
                    extra = {
                        "smtp_error": {
                            "email": self.email,
                            "message": str(exception),
                            "traceback": "".join(traceback.format_tb(exception.__traceback__)),
                        },
                    },
                )

                if(retry_count == 2):
                    self.process_invalid_smtp_response("Email domain connection error")
            retry_count += 1

    def process_invalid_smtp_response(self, message):
        redis.set_val(
            "dns.invalid_emails.{0}".format(self.email),
            message,
            settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)
        self.raise_exception(message)

    def raise_exception(self, message):
        if self.show_support_message:
            raise ForgotPassword(message)
        else:
            raise ForgotPassword(message)

class UserVerifyService(object):
    @staticmethod
    def _get_user_state(user, deeplink_params):
        deeplink_map = {
            "U001": deeplinks.LOGIN_SCREEN.format(deeplink_params),
            "U002": deeplinks.OTP_SCREEN.format(deeplink_params + "&intent=registration"),
        }
        user_status = "U001" if user else "U002"

        state = {
            "user_status": user_status,
            "redirect_url":  deeplink_map[user_status],
        }
        return state

    @staticmethod
    async def get_user_state_by_email(redis_client, email, db_session):
        user_rows = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                "email": email,
                "mobile": None,
                "calling_code": None,
            },
            db_session=db_session,
        )
        user = user_rows[0] if user_rows else None

        if not user:
            # email_dns_verify_service = EmailDnsVerifyService(email=email, show_support_message=False)
            # email_dns_verify_service.verify()
            await GenerateOtpService.generate_otp(redis_client, email, "email", Intent.REGISTRATION, db_session=db_session)
        return UserVerifyService._get_user_state(user, "email={}".format(email))

    @staticmethod
    def get_user_by_email(email):
        user = user.objects.filter(email=email).first()
        return user

    @staticmethod
    def get_user_by_mobile(mobile, calling_code):
        user = user.objects.filter(mobile=mobile, calling_code=calling_code).first()
        return user

    @staticmethod
    async def get_user_state_by_mobile(redis_client, mobile, calling_code, x_forwarded_for, db_session):
        user_rows = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                "email": None,
                "mobile": mobile,
                "calling_code": calling_code,
            },
            db_session=db_session,
        )
        user = user_rows[0] if user_rows else None

        if not user:
            MobileVerificationService.mobile_verification_service(mobile, calling_code)
            await GenerateOtpService.generate_otp(redis_client, calling_code+mobile, "mobile", Intent.REGISTRATION, x_forwarded_for, db_session=db_session)
        return UserVerifyService._get_user_state(user, "mobile=+{}-{}".format(calling_code, mobile))
    

class UserAuthService:

    @staticmethod
    async def login_with_mobile(session, mobile: str, calling_code: str, password: str, client, device_id: str, payload, request):
        result = await session.execute(
            select(User).where(
                User.mobile == mobile,
                User.calling_code == calling_code,
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise MobileNotRegistered()

        payload.update({
            "provider": "mobile",
            "id": mobile,
            "calling_code": calling_code,
            "email": user.email,
            "type": "force",
        })

        return await UserLoginService.login(
            session=session,
            user=user,
            payload=payload,
            client=client,
            device_id=device_id,
            request=request,
        )
        
    @staticmethod
    async def login_with_email(session, email: str, password: str, client, device_id: str, payload, request):
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise EmailNotRegistered()

        payload.update({
            "email": email,
            "type": "force",
        })

        return await UserLoginService.login(
            session=session,
            user=user,
            payload=payload,
            client=client,
            device_id=device_id,
            request=request,
        )
        
class UserRegisterService:

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str | None = None,
        mobile: str | None = None,
        password: str = "",
        name: str = "",
        calling_code: str | None = None,
        country: str | None = None,
        platform: str | None = None,
        activated: str = "YES",
        user_agent: str | None = None,
    ) -> User:

        firstname, lastname = UserProfileService.set_first_name_and_last_name(name)
        user_uuid = uuid.uuid4()
        now = datetime.datetime.now(pytz.utc)

        legacy_user = User(
            uuid=user_uuid,
            email=email,
            mobile=mobile,
            calling_code=calling_code,
            activation_code=get_random_bigint(),
            country=country,
            registration_datetime=now,
            updated_datetime=now,
            password=get_sha1_hash(password),
            encrypted_password=get_hashed_password(password),
            reg_user_agent=user_agent,
            activated=activated,
            name=name,
            firstname=firstname,
            lastname=lastname,
        )

        db.add(legacy_user)
        await db.flush()

        await UserRegisterService.create_pg_user(
            db=db,
            legacy_user=legacy_user,
            platform=platform,
        )

        await db.commit()
        return legacy_user


class UserProfileService:
    async def set_first_name_and_last_name(name):
        if name:
            name_array = name.rsplit(' ', 1)
            if len(name_array) > 1:
                return name_array[0], name_array[1]
            else:
                return name_array[0] if name_array[0] else None, None
        else:
            return None, None


class DeviceService:

    @staticmethod
    async def is_device_registered(db: AsyncSession, device_id: str) -> bool:
        stmt = select(func.count()).select_from(Device).where(Device.device_id == device_id)
        return (await db.scalar(stmt)) > 0

    @staticmethod
    async def create_device(
        db: AsyncSession,
        device_id: str,
        **attrs
    ) -> Device:

        if await DeviceService.is_device_registered(db, device_id):
            raise exceptions.DeviceAlreadyRegistered()

        device = Device(device_id=device_id, **attrs)
        db.add(device)
        await db.flush()

        user_uuid = attrs.get("uuid")

        if device.push_token and user_uuid:
            try:
                redis_service = DeviceTokenRedisService()
                sync_result = redis_service.store_device_token_in_redis(device, user_uuid)
                logger.info(f"Device token sync result for {device_id}: {sync_result}")
            except Exception as e:
                logger.error(f"Failed to sync device token for {device_id}: {e}")

        await db.commit()
        return device
    
    @staticmethod
    async def update_device(
        db: AsyncSession,
        device_id: str,
        **kwargs
    ) -> None:

        await db.execute(
            update(Device)
            .where(Device.device_id == device_id)
            .values(**kwargs)
        )

        if kwargs.get("push_token"):
            try:
                stmt = select(Device).where(
                    Device.device_id == device_id,
                    Device.uuid.isnot(None),
                    Device.device_active == 1
                )
                devices = (await db.scalars(stmt)).all()

                redis_service = DeviceTokenRedisService()
                for device in devices:
                    sync_result = redis_service.store_device_token_in_redis(
                        device, device.uuid
                    )
                    logger.info(
                        f"Device token sync result for {device_id} (user {device.uuid}): {sync_result}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to sync device token for {device_id} during update: {e}"
                )

        await db.commit()

    @staticmethod
    async def get_device_attrs(db: AsyncSession, device_id: str) -> dict:

        if not await DeviceService.is_device_registered(db, device_id):
            raise exceptions.DeviceNotRegistered()

        stmt = (
            select(Device)
            .where(Device.device_id == device_id)
            .order_by(Device.id.desc())
        )
        device = await db.scalar(stmt)

        return {
            "device_type": device.device_type,
            "device_name": device.device_name,
            "device_id": device.device_id,
        }

    @staticmethod
    async def get_device(db: AsyncSession, device_id: str) -> Device:

        if not await DeviceService.is_device_registered(db, device_id):
            raise exceptions.DeviceNotRegistered()

        stmt = (
            select(Device)
            .where(Device.device_id == device_id)
            .order_by(Device.id.desc())
        )
        return await db.scalar(stmt)

    @staticmethod
    async def link_device_to_user(
        db: AsyncSession,
        device_id: str,
        uuid,
        auth_token: str | None = None,
        skipped_legacy_login: bool = False,
    ) -> None:

        if not await DeviceService.is_device_registered(db, device_id):
            raise exceptions.DeviceNotRegistered()

        if isinstance(uuid, str):
            uuid = uuid_module.UUID(uuid)

        stmt = select(Device).where(
            Device.device_id == device_id,
            Device.uuid == uuid
        )
        device = await db.scalar(stmt)

        if not device:
            stmt = select(Device).where(
                Device.device_id == device_id,
                Device.uuid.is_(None)
            ).order_by(Device.id.desc())
            device = await db.scalar(stmt)

        if not device:
            base_device = await db.scalar(
                select(Device).where(Device.device_id == device_id)
            )
            device = clone_object(base_device)
            device.uuid = uuid
            db.add(device)

        device.user_token = auth_token
        device.uuid = uuid
        device.device_active = 1
        device.date_activated = datetime.datetime.now(pytz.utc)

        await db.flush()

        if device.push_token:
            try:
                redis_service = DeviceTokenRedisService()
                sync_result = redis_service.store_device_token_in_redis(device, uuid)
                loggers.info(f"Device token sync result for {device_id}: {sync_result}")
            except Exception as e:
                loggers.error(f"Failed to sync device token for {device_id}: {e}")

        if skipped_legacy_login:
            stmt = select(UserDeviceMap).where(
                UserDeviceMap.device_id == device_id,
                UserDeviceMap.uuid == uuid
            )
            udm = await db.scalar(stmt)

            if not udm:
                udm = UserDeviceMap(
                    uuid=uuid,
                    device_id=device_id,
                    device_name=device.device_name,
                    device_type=device.device_type,
                    device_ip=device.device_ip,
                    drm_type=device.drm_type,
                    transaction_type="STREAMING",
                    device_active=1,
                    date_activated=device.date_activated,
                    is_rooted=0,
                    is_jailbroken=0,
                    is_ip_legal=1,
                    is_anonymous_proxy=0,
                    residency_verified=1,
                    hardware_encryption=0,
                )
                db.add(udm)
            else:
                udm.device_active = 1
                udm.date_activated = device.date_activated
                udm.transaction_type = "STREAMING"

        await db.commit()

    @staticmethod
    async def get_active_devices_count(db: AsyncSession, uuid) -> int:
        stmt = select(func.count()).select_from(UserDeviceMap).where(
            UserDeviceMap.uuid == uuid,
            UserDeviceMap.device_active == 1,
            UserDeviceMap.transaction_type == "STREAMING"
        )
        return await db.scalar(stmt)

    @staticmethod
    async def deactivate_device(
        db: AsyncSession,
        device_id: str,
        uuid,
        skipped_legacy_login: bool = False,
    ) -> None:

        stmt = select(Device).where(Device.device_id == device_id, Device.uuid == uuid)
        device = await db.scalar(stmt)

        await db.execute(
            update(Device)
            .where(Device.device_id == device_id, Device.uuid == uuid)
            .values(
                device_active=0,
                date_deactivated=datetime.datetime.now(pytz.utc),
            )
        )

        if skipped_legacy_login:
            await db.execute(
                update(UserDeviceMap)
                .where(UserDeviceMap.device_id == device_id, UserDeviceMap.uuid == uuid)
                .values(
                    device_active=0,
                    date_deactivated=datetime.datetime.now(pytz.utc),
                )
            )

        if device and device.push_token:
            try:
                redis_service = DeviceTokenRedisService()
                sync_result = redis_service.remove_device_token_from_redis(device, uuid)
                loggers.info(
                    f"Device token removal result for {device_id}: {sync_result}"
                )
            except Exception as e:
                loggers.error(
                    f"Failed to remove device token for {device_id}: {e}"
                )

        await db.commit()

    @staticmethod
    async def map_to_gcm(
        db: AsyncSession,
        device: Device,
        uuid,
        country_code: str | None = None,
        app_version: str | None = None,
    ) -> None:

        try:
            stmt = select(GobeGcmMap).where(
                GobeGcmMap.gcm_id == device.push_token,
                GobeGcmMap.uuid == uuid,
            )
            gcm = await db.scalar(stmt)

            if gcm:
                gcm.device_id = device.device_id
                gcm.device_type = device.device_type.lower()
                gcm.country_code = country_code
                gcm.app_version = app_version
            else:
                db.add(
                    GobeGcmMap(
                        gcm_id=device.push_token,
                        uuid=uuid,
                        device_id=device.device_id,
                        device_type=device.device_type.lower(),
                        country_code=country_code,
                        app_version=app_version,
                    )
                )

            await db.commit()

        except Exception:
            logger.error(
                f"device not registered for device_id: {device.device_id}"
            )


class DeviceTokenRedisService:
    """
    Async service to store device tokens in Redis
    for eros_universe_device consumption
    """

    def __init__(self, redis: redis):
        self.redis = redis
        self.ttl = getattr(settings, "DEVICE_TOKEN_CACHE_TTL", 86400)  # 24h

    # ---------- Public APIs ----------

    async def store_device_token(self, device, user_uuid: str) -> dict:
        if not device.push_token:
            logger.info(
                f"No push token for device {device.device_id}, skipping Redis store"
            )
            return {"success": False, "message": "No push token"}

        try:
            device_key = self._device_key(user_uuid, device.device_id)
            index_key = self._user_index_key(user_uuid)

            device_data = {
                "token": device.push_token,
                "device_id": device.device_id,
                "device_type": device.device_type or "android",
                "device_name": device.device_name or "",
                "platform": device.platform or "android",
                "is_active": device.device_active == 1,
                "updated_at": datetime.datetime.utcnow().isoformat(),
            }

            # Store device token
            await self.redis.setex(
                device_key,
                self.ttl,
                json.dumps(device_data),
            )

            # Maintain index for this user
            await self.redis.sadd(index_key, device_key)
            await self.redis.expire(index_key, self.ttl)

            logger.info(f"Device token stored in Redis for {device.device_id}")
            return {"success": True}

        except Exception as exc:
            logger.error(f"Redis store failed: {exc}")
            return {"success": False, "error": str(exc)}

    async def remove_device_token(self, device, user_uuid: str) -> dict:
        try:
            device_key = self._device_key(user_uuid, device.device_id)
            index_key = self._user_index_key(user_uuid)

            await self.redis.delete(device_key)
            await self.redis.srem(index_key, device_key)

            logger.info(f"Device token removed for {device.device_id}")
            return {"success": True}

        except Exception as exc:
            logger.error(f"Redis delete failed: {exc}")
            return {"success": False, "error": str(exc)}

    async def get_user_device_tokens(self, user_uuid: str) -> List[dict]:
        try:
            index_key = self._user_index_key(user_uuid)
            device_keys = await self.redis.smembers(index_key)

            if not device_keys:
                return []

            values = await self.redis.mget(*device_keys)

            devices: List[dict] = []
            for value in values:
                if not value:
                    continue
                data = json.loads(value)
                if data.get("is_active"):
                    devices.append(data)

            return devices

        except Exception as exc:
            logger.error(f"Redis fetch failed for user {user_uuid}: {exc}")
            return []

    async def sync_all_user_devices(self, user_uuid: str, devices: list) -> dict:
        """
        Sync DB devices → Redis
        `devices` must be fetched by caller (SQLAlchemy async)
        """
        synced = 0

        for device in devices:
            result = await self.store_device_token(device, user_uuid)
            if result.get("success"):
                synced += 1

        logger.info(f"Synced {synced} devices to Redis for user {user_uuid}")
        return {"success": True, "synced_count": synced}

    # ---------- Internal helpers ----------

    @staticmethod
    def _device_key(user_uuid: str, device_id: str) -> str:
        return f"device_token:{user_uuid}:{device_id}"

    @staticmethod
    def _user_index_key(user_uuid: str) -> str:
        return f"user_device_index:{user_uuid}"
