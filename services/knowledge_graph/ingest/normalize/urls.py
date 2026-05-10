from urllib.parse import parse_qs, urlparse, urlunparse

from pydantic import HttpUrl


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}


def canonicalize_url(url: HttpUrl | str) -> str:
    if isinstance(url, HttpUrl):
        url_str = str(url)
    else:
        url_str = url

    parsed = urlparse(url_str)

    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS}

    new_query = "&".join(f"{k}={v[0]}" if len(v) == 1 else f"{k}={','.join(v)}" for k, v in filtered_params.items())

    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            new_query,
            "",
        )
    )

    if normalized.endswith("/"):
        normalized = normalized[:-1]

    return normalized

