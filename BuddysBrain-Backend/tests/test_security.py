from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import urllib3

from app.utils import safe_fetch
from app.utils.processing import ProcessingError

RESOURCE_ID = "507f1f77bcf86cd799439011"


@pytest.mark.parametrize("authorization", [None, "Bearer incorrect", "Basic abc"])
def test_delete_denies_untrusted_callers(client, db, monkeypatch, authorization):
    monkeypatch.setenv("RESOURCE_ADMIN_TOKEN", "test-admin-secret")
    response = client.delete(f"/resources/{RESOURCE_ID}", headers={"Authorization": authorization} if authorization else {})
    assert response.status_code == 401
    db.delete_one.assert_not_called()


def test_delete_fails_closed_when_unconfigured(client, db):
    assert client.delete(f"/resources/{RESOURCE_ID}").status_code == 503
    db.delete_one.assert_not_called()


def test_delete_allows_admin(client, db, monkeypatch):
    monkeypatch.setenv("RESOURCE_ADMIN_TOKEN", "test-admin-secret")
    db.delete_one.return_value = SimpleNamespace(deleted_count=1)
    response = client.delete(f"/resources/{RESOURCE_ID}", headers={"Authorization": "Bearer test-admin-secret"})
    assert response.status_code == 200
    db.delete_one.assert_awaited_once()


def dns(*addresses):
    return [(2, 1, 6, "", (address, 443)) for address in addresses]


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com", "https://user:secret@example.com", "https://example.com:8080", "https://example.com\\@localhost", "https://example.com\n"])
def test_rejects_unsafe_url_syntax(url):
    with pytest.raises(safe_fetch.UnsafeURL):
        safe_fetch.public_destination(url)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.0.1", "169.254.169.254", "::1", "fc00::1", "::ffff:127.0.0.1", "224.0.0.1"])
def test_blocks_internal_destinations(monkeypatch, address):
    monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", lambda *a, **k: dns(address))
    with pytest.raises(safe_fetch.UnsafeURL):
        safe_fetch.fetch_article_text("https://example.com")


def test_rejects_mixed_public_and_private_dns(monkeypatch):
    monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", lambda *a, **k: dns("93.184.216.34", "127.0.0.1"))
    with pytest.raises(safe_fetch.UnsafeURL):
        safe_fetch.public_destination("https://example.com")


def public_pool(monkeypatch, response):
    resolver = Mock(return_value=dns("93.184.216.34"))
    monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", resolver)
    pool = Mock()
    pool.request.return_value = response
    constructor = Mock(return_value=pool)
    monkeypatch.setattr(safe_fetch.urllib3, "HTTPSConnectionPool", constructor)
    return pool, constructor, resolver


def test_connects_to_validated_ip_with_original_tls_hostname(monkeypatch):
    response = Mock(status=200, headers={"Content-Type": "text/html"})
    response.stream.return_value = [b"Public article"]
    pool, constructor, resolver = public_pool(monkeypatch, response)
    assert safe_fetch.fetch_article_text("https://example.com/lesson") == "Public article"
    assert constructor.call_args.args == ("93.184.216.34", 443)
    assert constructor.call_args.kwargs["server_hostname"] == "example.com"
    assert constructor.call_args.kwargs["assert_hostname"] == "example.com"
    assert constructor.call_args.kwargs["cert_reqs"] == "CERT_REQUIRED"
    assert pool.request.call_args.kwargs["redirect"] is False
    assert pool.request.call_args.kwargs["headers"]["Host"] == "example.com"
    resolver.assert_called_once()
    response.close.assert_called_once()
    pool.close.assert_called_once()


def test_redirect_to_internal_address_is_blocked(monkeypatch):
    response = Mock(status=302, headers={"Location": "http://127.0.0.1/secret"})
    pool, _, resolver = public_pool(monkeypatch, response)
    resolver.side_effect = [dns("93.184.216.34"), dns("127.0.0.1")]
    with pytest.raises(safe_fetch.UnsafeURL):
        safe_fetch.fetch_article_text("https://example.com")
    pool.request.assert_called_once()
    response.close.assert_called_once()


def test_download_size_limit(monkeypatch):
    response = Mock(status=200, headers={"Content-Type": "text/plain"})
    response.stream.return_value = [b"x" * 33]
    public_pool(monkeypatch, response)
    monkeypatch.setattr(safe_fetch, "MAX_BYTES", 32)
    with pytest.raises(ProcessingError) as error:
        safe_fetch.fetch_article_text("https://example.com")
    assert error.value.status_code == 413


def test_download_timeout_is_useful_and_closes_pool(monkeypatch):
    pool, constructor, _ = public_pool(monkeypatch, None)
    pool.request.side_effect = urllib3.exceptions.ReadTimeoutError(None, "/", "timeout")
    with pytest.raises(ProcessingError) as error:
        safe_fetch.fetch_article_text("https://example.com")
    assert error.value.status_code == 504
    assert constructor.call_args.kwargs["timeout"].connect_timeout <= 5
    assert constructor.call_args.kwargs["timeout"].read_timeout <= 10
    pool.close.assert_called_once()
