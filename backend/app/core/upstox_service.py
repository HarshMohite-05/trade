import requests
import upstox_client
from upstox_client.rest import ApiException
from typing import Dict, Any, Optional
from ..config import current_settings, save_settings

class UpstoxService:
    def __init__(self):
        self.api_version = "2.0"

    def get_auth_url(self, api_key: Optional[str] = None, redirect_uri: Optional[str] = None) -> str:
        key = api_key or current_settings.api_key
        redirect = redirect_uri or current_settings.redirect_uri
        return f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={key}&redirect_uri={redirect}"

    def exchange_code_for_token(self, code: str, api_key: str, api_secret: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchanges the authorization code for access token using Upstox API v2.
        """
        url = "https://api.upstox.com/v2/login/authorization/token"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "code": code,
            "client_id": api_key,
            "client_secret": api_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        response = requests.post(url, headers=headers, data=data)
        res_data = response.json()
        
        if response.status_code == 200 and "access_token" in res_data:
            current_settings.api_key = api_key
            current_settings.api_secret = api_secret
            current_settings.redirect_uri = redirect_uri
            current_settings.access_token = res_data["access_token"]
            current_settings.user_name = res_data.get("user_name", "")
            current_settings.user_id = res_data.get("user_id", "")
            save_settings(current_settings)
            return {"status": "success", "data": res_data}
        else:
            error_msg = res_data.get("errors", [{"message": "Token exchange failed"}])[0].get("message", "Unknown error")
            return {"status": "error", "message": error_msg, "details": res_data}

    def set_manual_token(self, token: str, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> Dict[str, Any]:
        """Allows directly saving an active access token"""
        current_settings.access_token = token.strip()
        if api_key:
            current_settings.api_key = api_key.strip()
        if api_secret:
            current_settings.api_secret = api_secret.strip()
            
        # Test the token by fetching user profile
        profile = self.get_profile(token.strip())
        if profile.get("status") == "success":
            user_data = profile.get("data", {})
            current_settings.user_name = user_data.get("user_name", "")
            current_settings.user_id = user_data.get("user_id", "")
            save_settings(current_settings)
            return {"status": "success", "message": "Token verified and saved", "profile": user_data}
        else:
            # Still save token in case profile API fails due to permissions but token is valid
            save_settings(current_settings)
            return {"status": "warning", "message": "Token saved, but profile check returned an error", "error": profile.get("message")}

    def get_api_client(self, token: Optional[str] = None) -> upstox_client.ApiClient:
        tok = token or current_settings.access_token
        if not tok:
            raise ValueError("No Upstox access token configured. Please authenticate first.")
        configuration = upstox_client.Configuration()
        configuration.access_token = tok
        return upstox_client.ApiClient(configuration)

    def get_profile(self, token: Optional[str] = None) -> Dict[str, Any]:
        try:
            client = self.get_api_client(token)
            api_instance = upstox_client.UserApi(client)
            api_response = api_instance.get_profile(self.api_version)
            return {"status": "success", "data": api_response.data.to_dict()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_market_quote(self, instrument_key: str = "NSE_EQ|INE002A01018") -> Dict[str, Any]:
        """
        Pulls market quote/tick for a given instrument.
        Default is RELIANCE (NSE_EQ|INE002A01018).
        """
        try:
            client = self.get_api_client()
            api_instance = upstox_client.MarketQuoteApi(client)
            api_response = api_instance.get_full_market_quote(instrument_key, self.api_version)
            raw_dict = api_response.data
            # Convert response objects to dict
            formatted = {}
            for k, v in raw_dict.items():
                formatted[k] = v.to_dict() if hasattr(v, "to_dict") else str(v)
            return {"status": "success", "instrument_key": instrument_key, "data": formatted}
        except ApiException as e:
            return {"status": "error", "message": f"Upstox API Error: {e.body or str(e)}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_batch_quotes(self, instrument_keys: list[str]) -> Dict[str, Any]:
        """
        Pulls batch live quotes for multiple instruments in one API call.
        """
        try:
            tok = current_settings.access_token
            if not tok:
                return {"status": "error", "message": "No Upstox access token configured."}
            keys_param = ",".join(instrument_keys)
            url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={keys_param}"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {tok}"
            }
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", {})
                return {"status": "success", "data": data}
            else:
                return {"status": "error", "message": f"Upstox HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_historical_candles_range(self, instrument_key: str, to_date: str, from_date: str, interval: str = "1minute") -> list:
        """
        Pulls real historical candles directly from Upstox API v2.
        Returns list of candles in chronological order [timestamp, open, high, low, close, volume, oi].
        """
        try:
            import urllib.parse
            tok = current_settings.access_token
            if not tok:
                return []
            encoded_key = urllib.parse.quote(instrument_key)
            url = f"https://api.upstox.com/v2/historical-candle/{encoded_key}/{interval}/{to_date}/{from_date}"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {tok}"
            }
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                candles = res.json().get("data", {}).get("candles", [])
                # Upstox returns candles in reverse chronological order (latest first). Reverse to chronological:
                candles.reverse()
                return candles
            return []
        except Exception as e:
            print(f"Error fetching historical candles for {instrument_key}: {e}")
            return []

upstox_service = UpstoxService()

