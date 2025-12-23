import datetime
import pytz
from app.api.v1.register import redis
from app.core.constants import AuthConfig
from app.db.models.user_app import AppConsumer, User
import jwt
from app.settings import settings


class AuthService(object):

    @staticmethod
    def generate_token(user, client_id, device_id=None, days_to_expire=settings.USER_TOKEN_DAYS_TO_EXPIRE, partner_attrs={}):
        application = AppConsumer.objects.get(client_id=client_id)
        partner_code = application.partner_code 
        expiry = datetime.datetime.now(pytz.utc) + datetime.timedelta(days=days_to_expire)
        token_payload = {
            "uuid": str(user.uuid),
            "exp": expiry
        }

        encoded_jwt = jwt.encode(token_payload, application.client_secret, algorithm=AuthConfig.ALGORITHM).decode(AuthConfig.DECODE_CODE)

        # save token in table
        User.objects.create(
            device_id=device_id,
            token=encoded_jwt,
            uuid=user.uuid,
            app_consumer=application,
            expires_at=expiry,
            partner_id=partner_attrs.get('partner_id', None),
        )
        # generated token needs to be saved in redis
        # TODO we need to remove this from next release after MX is set
        if not partner_code in settings.SKIP_PARTNER_AUTH_REDIS_CHECK:
            redis.lpush(str(user.uuid), encoded_jwt)

            timeout_val = int(((expiry + datetime.timedelta(days=settings.TOKEN_LEEWAY_THRESHOLD_IN_DAYS)).timestamp()) - datetime.datetime.now(pytz.utc).timestamp())
            redis.set_val(encoded_jwt, str(user.uuid), timeout=timeout_val)
        
        return encoded_jwt, int(expiry.timestamp())

