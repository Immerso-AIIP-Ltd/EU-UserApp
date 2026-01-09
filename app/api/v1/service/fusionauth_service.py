
import os
import requests
import json
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, status
from fusionauth.fusionauth_client import FusionAuthClient
from app.settings import settings

# Global cache for JWKS
_jwks_client = None

class FusionAuthService:
    @staticmethod
    def get_jwks_url():
        return f"{settings.fusionauth_url}/.well-known/jwks.json"

    @staticmethod
    def get_client():
        return FusionAuthClient(settings.fusionauth_api_key, settings.fusionauth_url)

    @classmethod
    def get_jwks_client(cls):
        global _jwks_client
        if _jwks_client is None:
            _jwks_client = PyJWKClient(cls.get_jwks_url())
        return _jwks_client

    @classmethod
    def verify_token(cls, token: str):
        try:
            jwks_client = cls.get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.fusionauth_client_id
            )
            return payload
        except Exception as e:
            # print(f"Token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Could not validate credentials")

    @classmethod
    def create_fusion_user(cls, user_uuid: str, email: str = None):
        """
        Creates a user in FusionAuth with the local user_uuid as the FusionAuth User ID.
        If email is provided, it is set. If not, the user_uuid is used as the username.
        """
        client = cls.get_client()
        
        user_body = {
            "password": None # No password in FA
        }
        if email:
            user_body["email"] = email
        else:
            user_body["username"] = user_uuid

        user_request = {
            "user": user_body,
            "registration": {
                "applicationId": settings.fusionauth_client_id
            },
            "skipVerification": True
        }
        
        # Check if user exists by ID first
        search_response = client.retrieve_user(user_uuid)
        if search_response.was_successful():
            user = search_response.success_response["user"]
            registrations = user.get("registrations", [])
            is_registered = any(r["applicationId"] == settings.fusionauth_client_id for r in registrations)
            
            if not is_registered:
                # Use keyword args for safety
                reg_response = client.register(user_id=user_uuid, request={
                    "registration": {
                        "applicationId": settings.fusionauth_client_id
                    }
                })
                if not reg_response.was_successful():
                     # print(f"Failed to register existing user: {reg_response.error_response}")
                     raise HTTPException(status_code=500, detail="Failed to register user to application")

            return user_uuid
        
        # Create new user
        # Use keyword args for safety
        response = client.register(user_id=user_uuid, request=user_request)

        if response.was_successful():
            return response.success_response["user"]["id"]
        else:
            # print(f"Failed to create FA user: {response.error_response}")
            raise HTTPException(status_code=500, detail="Failed to sync user with Authentication Provider")

    @classmethod
    def issue_token(cls, fusion_user_id: str, roles: list = None, user_details: dict = None):
        """
        Issues a JWT for the specified user from FusionAuth using the Vend API.
        """
        client = cls.get_client()
        
        claims = {
            "sub": fusion_user_id,
            "aud": settings.fusionauth_client_id,
            "iss": settings.fusionauth_url,
            "roles": roles or []
        }
        
        if user_details:
            claims.update(user_details)

        jwt_request = {
            "claims": claims,
            "timeToLiveInSeconds": 600
        }
        
        response = client.vend_jwt(jwt_request)
        
        if response.was_successful():
            return response.success_response["token"]
        else:
            # print(f"Failed to issue token: {response.error_response}")
            raise HTTPException(status_code=500, detail="Authentication Provider could not issue token")
