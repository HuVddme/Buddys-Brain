"""Fetch public articles without trusting redirects, DNS changes or proxies."""

import ipaddress
import socket
import time
from urllib.parse import quote, urljoin, urlsplit

import urllib3

from .processing import ProcessingError

MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3


class UnsafeURL(ProcessingError):
    def __init__(self, message="Use a public HTTP or HTTPS article URL."):
        super().__init__(message, 400)


def public_destination(url):
    try:
        parts = urlsplit(url)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None
                or any(ord(char) < 32 or ord(char) == 127 for char in url)
                or "\\" in url):
            raise UnsafeURL()
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if port not in {80, 443}:
            raise UnsafeURL("Article URLs must use port 80 or 443.")
        hostname = parts.hostname.encode("idna").decode("ascii")
        addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        ips = [ipaddress.ip_address(item[4][0]) for item in addresses]
        # Reject a hostname even if just one of its answers is private.
        if not ips or any(not ip.is_global or ip.is_multicast for ip in ips):
            raise UnsafeURL()
        return parts, hostname, port, str(ips[0])
    except UnsafeURL:
        raise
    except (ValueError, UnicodeError) as exc:
        raise UnsafeURL() from exc
    except OSError as exc:
        raise ProcessingError("The article host could not be reached.") from exc


def fetch_article_text(url):
    deadline = time.monotonic() + 30
    for redirect in range(MAX_REDIRECTS + 1):
        parts, hostname, port, address = public_destination(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProcessingError("The article download timed out.", 504)
        options = {"timeout": urllib3.Timeout(connect=min(5, remaining), read=min(10, remaining)),
                   "retries": False}
        # Connect to the validated IP, preserving the original Host/SNI and
        # certificate verification. A second DNS lookup cannot redirect us.
        if parts.scheme == "https":
            pool = urllib3.HTTPSConnectionPool(
                address, port, server_hostname=hostname,
                assert_hostname=hostname, cert_reqs="CERT_REQUIRED", **options,
            )
        else:
            pool = urllib3.HTTPConnectionPool(address, port, **options)
        response = None
        try:
            host_header = f"[{hostname}]" if ":" in hostname else hostname
            if port != (443 if parts.scheme == "https" else 80):
                host_header += f":{port}"
            target = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
            if parts.query:
                target += "?" + quote(parts.query, safe="%=&/:?@!$'()*+,;~-._")
            response = pool.request(
                "GET", target, headers={"Host": host_header, "Accept-Encoding": "identity"},
                redirect=False, preload_content=False,
            )
            if response.status in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if not location or redirect == MAX_REDIRECTS:
                    raise ProcessingError("The article has too many or invalid redirects.")
                url = urljoin(url, location)
                continue
            if response.status >= 400:
                raise ProcessingError("The article website could not provide this page.")
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                raise ProcessingError("This URL is not a supported article. Upload documents instead.", 415)
            if response.headers.get("Content-Encoding", "identity").lower() not in {"", "identity"}:
                raise ProcessingError("The article returned an unsupported compressed response.")
            body = bytearray()
            for chunk in response.stream(16 * 1024, decode_content=False):
                if time.monotonic() > deadline:
                    raise ProcessingError("The article download timed out.", 504)
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ProcessingError("The article is too large to process.", 413)
            return body.decode("utf-8", errors="replace")
        except urllib3.exceptions.TimeoutError as exc:
            raise ProcessingError("The article download timed out.", 504) from exc
        except urllib3.exceptions.HTTPError as exc:
            raise ProcessingError("The article could not be downloaded.") from exc
        finally:
            if response is not None:
                response.close()
            pool.close()
