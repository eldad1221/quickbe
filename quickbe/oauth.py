import os
import pathlib
import datetime
import requests
from cachetools import TTLCache
from quickbe.utils import load_env
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests
from google_auth_oauthlib.flow import Flow
from flask import abort, redirect, request
from quickbe import WebServer, HttpSession, endpoint, Log, get_env_var

AUTHORIZATION_FLOW_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]


# AUTHORIZATION_FLOW = Flow.from_client_secrets_file(
#     client_secrets_file='client_secrets_file',
#     scopes=AUTHORIZATION_FLOW_SCOPES,
#     redirect_uri="http://127.0.0.1:8888/hello"
# )
AUTHORIZATION_FLOW = None


def get_authorization_flow():
    global AUTHORIZATION_FLOW
    if AUTHORIZATION_FLOW is None:
        authorization_flow_redirect_uri = get_env_var('AUTHORIZATION_FLOW_REDIRECT_URI')
        authorization_flow_project_id = get_env_var('AUTHORIZATION_FLOW_PROJECT_ID')
        authorization_flow_client_id = get_env_var('AUTHORIZATION_FLOW_CLIENT_ID')
        authorization_flow_client_secret = get_env_var('AUTHORIZATION_FLOW_CLIENT_SECRET')
        authorization_flow_auth_uri = get_env_var('AUTHORIZATION_FLOW_AUTH_URI', "https://accounts.google.com/o/oauth2/auth")
        authorization_flow_token_uri = get_env_var('AUTHORIZATION_FLOW_TOKEN_URI', "https://oauth2.googleapis.com/token")
        authorization_flow_auth_provider_x509_cert_url = get_env_var(
            key='AUTHORIZATION_FLOW_AUTH_PROVIDER_X509_CERT_URL',
            default="https://www.googleapis.com/oauth2/v1/certs"
        )

        authorization_flow_client_config = {
          "web": {
            "client_id": authorization_flow_client_id,
            "client_secret": authorization_flow_client_secret,
            "project_id": authorization_flow_project_id,
            "auth_uri": authorization_flow_auth_uri,
            "token_uri": authorization_flow_token_uri,
            "auth_provider_x509_cert_url": authorization_flow_auth_provider_x509_cert_url,
            "redirect_uris": [authorization_flow_redirect_uri]
          }
        }
        AUTHORIZATION_FLOW = Flow.from_client_config(
            client_config=authorization_flow_client_config,
            scopes=AUTHORIZATION_FLOW_SCOPES,
            redirect_uri=authorization_flow_redirect_uri
        )

    return AUTHORIZATION_FLOW



