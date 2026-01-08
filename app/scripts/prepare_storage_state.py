import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_PATH = BASE_DIR.joinpath("secrets", "codeur_cookies_raw.json")
TARGET_PATH = BASE_DIR.joinpath("app", "services", "storage_state.json")

def normalize_cookie(raw_cookie: dict) -> dict:
    same_site_map = {
        "no_restriction": "None",
        "unspecified": "None",
        "lax": "Lax",
        "strict": "Strict",
        "none": "None",
    }
    return {
        "name": raw_cookie["name"],
        "value": raw_cookie["value"],
        "domain": raw_cookie.get("domain", ".codeur.com"),
        "path": raw_cookie.get("path", "/"),
        "expires": int(raw_cookie.get("expirationDate", -1)),
        "httpOnly": bool(raw_cookie.get("httpOnly", False)),
        "secure": bool(raw_cookie.get("secure", True)),
        "sameSite": same_site_map.get(raw_cookie.get("sameSite", "None"), "None"),
    }

def main() -> None:
    try:
        if not RAW_PATH.exists():
            print(f"Error: {RAW_PATH} does not exist")
            raise FileNotFoundError(f"File {RAW_PATH} does not exist")
        cookies = json.loads(RAW_PATH.read_text())
        normalized = [normalize_cookie(cookie) for cookie in cookies]
        storage_state = {"cookies": normalized, "origins": []}
        TARGET_PATH.write_text(json.dumps(storage_state, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        raise e

if __name__ == "__main__":
    main()