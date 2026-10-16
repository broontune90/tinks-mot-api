import os
import time
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import quote

app = FastAPI(title="Tinks Vehicle Check API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

TOKEN_URL = os.getenv("DVSA_TOKEN_URL", "")
CLIENT_ID = os.getenv("DVSA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DVSA_CLIENT_SECRET", "")
API_KEY = os.getenv("DVSA_API_KEY", "")
SCOPE = os.getenv(
    "DVSA_SCOPE",
    "https://tapi.dvsa.gov.uk/.default"
)

API_BASE = "https://history.mot.api.gov.uk"

_cached_token = None
_token_expiry = 0


def get_token():
    global _cached_token, _token_expiry

    if _cached_token and time.time() < _token_expiry:
        return _cached_token

    if not all([
        TOKEN_URL,
        CLIENT_ID,
        CLIENT_SECRET,
        API_KEY
    ]):
        raise HTTPException(
            status_code=503,
            detail="DVSA credentials have not been configured."
        )

    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": SCOPE,
            },
            timeout=20,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail="DVSA authentication failed. Check backend configuration."
            )

        data = response.json()
        _cached_token = data["access_token"]

        expires_in = int(data.get("expires_in", 3600))
        _token_expiry = time.time() + max(60, expires_in - 120)

        return _cached_token

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Could not contact DVSA authentication."
        )


@app.get("/")
def home():
    return {
        "app": "Tinks Vehicle Check",
        "status": "online"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/vehicle/{registration}")
def vehicle_check(registration: str):
    reg = "".join(registration.upper().split())

    if not reg or len(reg) > 10:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid vehicle registration."
        )

    token = get_token()

    url = (
        API_BASE
        + "/v1/trade/vehicles/registration/"
        + quote(reg, safe="")
    )

    try:
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": API_KEY,
                "Accept": "application/json",
            },
            timeout=25,
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="No MOT history was found for that registration."
            )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=502,
                detail="DVSA rejected the request. Check API access and credentials."
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"DVSA returned HTTP {response.status_code}."
            )

        return response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Could not contact the DVSA MOT service."
        )
