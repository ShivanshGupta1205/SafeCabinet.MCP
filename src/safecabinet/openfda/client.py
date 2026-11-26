import httpx
from dotenv import load_dotenv
import os
from .errors import NotFoundError, RateLimitExceededError, UpstreamError
load_dotenv()

BASE_URL = os.getenv("OPENFDA_BASE_URL", "https://api.fda.gov")
OPENFDA_API_KEY = os.getenv("OPENFDA_API_KEY")

def get(endpoint: str, search: str, limit:  int = 5, count: str | None = None) -> dict:
    """
    Makes a GET request to the OpenFDA API.

    Args:
        endpoint (str): The API endpoint to query.
        search (str): The search query.
        limit (int, optional): The maximum number of results to return. Defaults to 5.
        count (str | None, optional): The field to count occurrences of. Defaults to None.

    Returns:
        dict: The JSON response from the API.
    """
    params = {
        "search": search,
        "limit": limit
    }
    if count:
        params["count"] = count

    if OPENFDA_API_KEY:
        params["api_key"] = OPENFDA_API_KEY

    url = f"{BASE_URL}/{endpoint}.json"
    
    try:
        response = httpx.get(url, params=params, timeout=10)

    except httpx.RequestError as exc:
            raise UpstreamError(f"Request failed: {exc}") from exc

    code = response.status_code
    if code == 404:
        raise NotFoundError("The requested resource was not found.")
    if code == 429:
        raise RateLimitExceededError("The API rate limit has been exceeded.")
    if code >= 500:
        raise UpstreamError("An upstream server error occurred.")
    if code == 403:
        raise UpstreamError("Access forbidden. Check your API key and permissions.")

    response.raise_for_status()
    return response.json()
    


