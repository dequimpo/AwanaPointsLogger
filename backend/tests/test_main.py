import asyncio
import base64
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from pydantic import ValidationError

import main

TENANT = main.config["tenant_id"]
CLIENT_ID = main.config["client_id"]


@pytest.fixture(autouse=True)
def reset_limiter():
    main.limiter.reset()
    yield
    main.limiter.reset()


# ---------------------------------------------------------------- pure helpers


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-03-01", "2026-03-01"),
        ("3/1/2026", "2026-03-01"),
        ("03/01/2026", "2026-03-01"),
        ("3/1/26", "2026-03-01"),
        ("2026-03-01T10:15:00", "2026-03-01"),
        (46082, "2026-03-01"),
        (46082.0, "2026-03-01"),
        ("  2026-03-01  ", "2026-03-01"),
        ("", ""),
        (None, ""),
        ("not a date", "not a date"),
    ],
)
def test_normalize_date_str(value, expected):
    assert main.normalize_date_str(value) == expected


@pytest.mark.parametrize(
    "values,expected",
    [
        ([0, 0, 0, 0, 0, 0, 0, 0], 0),
        ([1, 1, 1, 1, 1, 0, 0, 0], 50),
        ([0, 0, 0, 0, 0, 1, 0, 0], 30),
        ([0, 0, 0, 0, 0, 0, 1, 1], 40),
        ([1, 1, 1, 1, 1, 1, 1, 1], 120),
        (["1", "", None, "x", 1], 20),
        ([1, 1], 20),
        ([], 0),
        ("not-a-list", 0),
    ],
)
def test_calculate_total_points_from_row_values(values, expected):
    assert main.calculate_total_points_from_row_values(values) == expected


POINTSLOG_ROWS = [
    ["Date", "StudentID", "Class", "Attendance"],
    ["2026-03-01", "S1", "Trek", 1],
    [46082, "S2", "Trek", 0],
    ["3/8/2026", " S1 ", "Trek", 0],
    ["2026-03-01", "S1", "Cubbies", 0],
    ["short"],
]


@pytest.mark.parametrize(
    "date_value,student_id,class_name,expected",
    [
        ("2026-03-01", "S1", "Trek", 2),
        ("3/1/2026", "S2", "Trek", 3),
        ("2026-03-08", "S1", "Trek", 4),
        ("2026-03-01", "S1", "Cubbies", 5),
        ("2026-03-01", "S3", "Trek", None),
        ("2026-03-15", "S1", "Trek", None),
    ],
)
def test_find_pointslog_row_index(date_value, student_id, class_name, expected):
    assert main.find_pointslog_row_index(POINTSLOG_ROWS, date_value, student_id, class_name) == expected


def test_find_pointslog_row_index_skips_header_only_sheet():
    assert main.find_pointslog_row_index([["Date", "StudentID", "Class"]], "2026-03-01", "S1", "Trek") is None


# ---------------------------------------------------------------- session tokens


def _user():
    return main.AuthUser(oid="oid-1", display_name="Leader", email="leader@example.org")


def test_session_token_round_trip():
    token, expires_in = main.create_session_token(_user())
    assert expires_in == main.SESSION_TTL_HOURS * 3600

    payload = main.require_authenticated_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    assert payload["sub"] == "oid-1"
    assert payload["name"] == "Leader"
    assert payload["aud"] == main.SESSION_AUDIENCE
    assert payload["iss"] == main.SESSION_ISSUER
    assert payload["exp"] > time.time()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: {**p, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        lambda p: {**p, "aud": "someone-else"},
        lambda p: {**p, "iss": "someone-else"},
    ],
)
def test_session_token_rejects_bad_claims(mutate):
    now = datetime.now(timezone.utc)
    base = {
        "sub": "oid-1",
        "iss": main.SESSION_ISSUER,
        "aud": main.SESSION_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    token = jwt.encode(mutate(base), main.config["session_secret"], algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        main.require_authenticated_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    assert exc.value.status_code == 401


def test_session_token_rejects_wrong_secret():
    token, _ = main.create_session_token(_user())
    forged = jwt.encode(jwt.decode(token, options={"verify_signature": False}), "other", algorithm="HS256")
    with pytest.raises(HTTPException):
        main.require_authenticated_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=forged))


def test_missing_session_token_rejected():
    with pytest.raises(HTTPException) as exc:
        main.require_authenticated_user(None)
    assert exc.value.status_code == 401


# ---------------------------------------------------------------- Entra token validation

_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_KID = "test-kid"


@pytest.fixture
def entra_jwks(monkeypatch):
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_RSA_KEY.public_key()))
    jwk["kid"] = _KID
    monkeypatch.setitem(main._jwks_cache, "keys", {_KID: jwk})
    monkeypatch.setitem(main._jwks_cache, "fetched_at", time.monotonic())


def _entra_claims(**overrides):
    now = int(time.time())
    claims = {
        "aud": "00000003-0000-0000-c000-000000000000",
        "iss": f"https://sts.windows.net/{TENANT}/",
        "tid": TENANT,
        "oid": "oid-1",
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return claims


def _sign(claims, headers=None):
    return jwt.encode(claims, _RSA_KEY, algorithm="RS256", headers={"kid": _KID, **(headers or {})})


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _graph_style_token(claims):
    """Mimic Graph tokens: the signed header holds sha256(nonce); the issued header holds the raw nonce."""
    nonce = "raw-nonce-value"
    signed = _sign(claims, headers={"nonce": hashlib.sha256(nonce.encode()).hexdigest()})
    header_b64, payload_b64, sig_b64 = signed.split(".")
    header = json.loads(base64.urlsafe_b64decode(header_b64 + "=" * (-len(header_b64) % 4)))
    header["nonce"] = nonce
    return ".".join([_b64(json.dumps(header, separators=(",", ":")).encode()), payload_b64, sig_b64])


@pytest.mark.anyio
@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"aud": "https://graph.microsoft.com"},
        {"aud": CLIENT_ID, "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0"},
        {"aud": f"api://{CLIENT_ID}"},
    ],
)
async def test_validate_entra_access_token_accepts_valid(entra_jwks, overrides):
    claims = await main.validate_entra_access_token(_sign(_entra_claims(**overrides)))
    assert claims["tid"] == TENANT


@pytest.mark.anyio
async def test_validate_entra_access_token_accepts_graph_nonce_token(entra_jwks):
    claims = await main.validate_entra_access_token(_graph_style_token(_entra_claims()))
    assert claims["oid"] == "oid-1"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "https://evil.example.com"},
        {"iss": "https://sts.windows.net/other-tenant/"},
        {"tid": "other-tenant"},
        {"exp": int(time.time()) - 3600},
    ],
)
async def test_validate_entra_access_token_rejects_bad_claims(entra_jwks, overrides):
    with pytest.raises(jwt.PyJWTError):
        await main.validate_entra_access_token(_sign(_entra_claims(**overrides)))


@pytest.mark.anyio
async def test_validate_entra_access_token_rejects_bad_signature(entra_jwks):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(_entra_claims(), other_key, algorithm="RS256", headers={"kid": _KID})
    with pytest.raises(jwt.InvalidSignatureError):
        await main.validate_entra_access_token(token)


@pytest.mark.anyio
async def test_validate_entra_access_token_rejects_unknown_kid(entra_jwks):
    token = jwt.encode(_entra_claims(), _RSA_KEY, algorithm="RS256", headers={"kid": "unknown"})
    with pytest.raises(jwt.InvalidTokenError):
        await main.validate_entra_access_token(token)


@pytest.mark.anyio
async def test_validate_entra_access_token_rejects_hs256(entra_jwks):
    token = jwt.encode(_entra_claims(), "secret", algorithm="HS256", headers={"kid": _KID})
    with pytest.raises(jwt.InvalidTokenError):
        await main.validate_entra_access_token(token)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------- models


def test_models_accept_valid_payload():
    update = main.StudentUpdate(date="2026-03-01", class_name="T&T", student_name="A", attendance=1)
    assert update.attendance == 1
    main.BootstrapRequest(date="3/1/2026", class_name="Cubbies")
    main.AutoPopulateRequest(date="2026-03-01", class_name="Journey_Boys")


@pytest.mark.parametrize(
    "payload",
    [
        {"date": "2026-02-30", "class_name": "Trek"},
        {"date": "yesterday", "class_name": "Trek"},
        {"date": "2026-03-01; DROP", "class_name": "Trek"},
        {"date": "2026-03-01", "class_name": "Sparks"},
    ],
)
def test_models_reject_bad_date_or_class(payload):
    for model in (main.BootstrapRequest, main.AutoPopulateRequest):
        with pytest.raises(ValidationError):
            model(**payload)
    with pytest.raises(ValidationError):
        main.StudentUpdate(student_name="A", **payload)


@pytest.mark.parametrize("value", [2, -1, 0.5])
def test_student_update_rejects_out_of_range_points(value):
    with pytest.raises(ValidationError):
        main.StudentUpdate(date="2026-03-01", class_name="Trek", student_name="A", bible=value)


@pytest.mark.parametrize("student_id", [None, "", "   "])
def test_normalized_update_requires_student_id(student_id):
    with pytest.raises(ValidationError):
        main.NormalizedStudentUpdate(
            date="2026-03-01", class_name="Trek", student_name="A", student_id=student_id
        )


# ---------------------------------------------------------------- endpoints with mocked Graph


class FakeGraph:
    def __init__(self, students, pointslog):
        self.students = students
        self.pointslog = pointslog
        self.patches = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "GET" and "worksheets('Students')" in url:
            return httpx.Response(200, json={"values": self.students})
        if request.method == "GET" and "worksheets('PointsLog')" in url:
            return httpx.Response(200, json={"values": self.pointslog})
        if request.method == "PATCH":
            address = url.split("address='")[1].split("'")[0]
            self.patches.append((address, json.loads(request.content)["values"]))
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"error": "unexpected"})


STUDENTS = [["StudentID", "Name", "Class"], ["S1", "Ann", "Trek"], ["S2", "Bob", "Trek"], ["S3", "Cy", "Cubbies"]]


@pytest.fixture
def fake_graph(monkeypatch):
    graph = FakeGraph(
        STUDENTS,
        [
            ["Date", "StudentID", "Class", "Att", "Bible", "BA", "MV", "Part", "B1", "B2", "B3", "Total"],
            ["2026-03-01", "S1", "Trek", 1, 0, 0, 0, 0, 0, 0, 0, 10],
        ],
    )
    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        assert kwargs.get("timeout") == main.HTTP_TIMEOUT
        return real_client(transport=httpx.MockTransport(graph.handler))

    monkeypatch.setattr(main.httpx, "AsyncClient", client_factory)
    return graph


@pytest.fixture
def client():
    main.app.dependency_overrides[main.get_graph_access_token] = lambda: "graph-token"
    token, _ = main.create_session_token(_user())
    with TestClient(main.app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client
    main.app.dependency_overrides.clear()


def test_update_existing_row_is_single_range_write(client, fake_graph):
    response = client.patch(
        "/sheets/PointsLog/update",
        json={"date": "2026-03-01", "class_name": "Trek", "student_name": "Ann", "student_id": "S1", "bonus1_baf_1": 1},
    )
    assert response.status_code == 200, response.text
    assert response.json()["total_points"] == 40
    assert fake_graph.patches == [("D2:L2", [[1, 0, 0, 0, 0, 1, 0, 0, 40]])]


def test_update_missing_row_appends_full_row_once(client, fake_graph):
    response = client.patch(
        "/sheets/PointsLogSheet/update",
        json={"date": "2026-03-01", "class_name": "Trek", "student_name": "Bob", "bible": 1},
    )
    assert response.status_code == 200, response.text
    assert fake_graph.patches == [("A3:L3", [["2026-03-01", "S2", "Trek", 0, 1, 0, 0, 0, 0, 0, 0, 10]])]


def test_normalized_update_rejects_missing_student_id(client, fake_graph):
    response = client.patch(
        "/sheets/PointsLog/update",
        json={"date": "2026-03-01", "class_name": "Trek", "student_name": "Ann", "bible": 1},
    )
    assert response.status_code == 422
    assert fake_graph.patches == []


def test_graph_write_failure_does_not_leak_body(client, fake_graph, monkeypatch):
    original = fake_graph.handler

    def failing(request):
        if request.method == "PATCH":
            return httpx.Response(500, text="secret graph internals")
        return original(request)

    monkeypatch.setattr(fake_graph, "handler", failing)
    response = client.patch(
        "/sheets/PointsLog/update",
        json={"date": "2026-03-01", "class_name": "Trek", "student_name": "Ann", "student_id": "S1", "bible": 1},
    )
    assert response.status_code == 400
    assert "secret graph internals" not in response.text


@pytest.mark.parametrize("path", ["/sheets/PointsLogSheet/bootstrap", "/sheets/PointsLog/auto-populate"])
def test_populate_endpoints_skip_existing_rows(client, fake_graph, path):
    response = client.post(path, json={"date": "3/1/2026", "class_name": "Trek"})
    assert response.status_code == 200, response.text
    assert response.json()["entries_created"] == 1
    assert fake_graph.patches == [("A3:L3", [["2026-03-01", "S2", "Trek", 0, 0, 0, 0, 0, 0, 0, 0, 0]])]


class StatefulGraph(FakeGraph):
    """Applies PATCHes to its PointsLog and yields between requests to expose races."""

    async def async_handler(self, request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.01)
        url = str(request.url)
        if request.method == "GET" and "worksheets('PointsLog')" in url:
            return httpx.Response(200, json={"values": [list(row) for row in self.pointslog]})
        response = self.handler(request)
        if request.method == "PATCH":
            address, values = self.patches[-1]
            start, _end = address.split(":")
            first_col = ord(start[0]) - ord("A")
            row_number = int(start[1:])
            for offset, row_values in enumerate(values):
                index = row_number - 1 + offset
                while len(self.pointslog) <= index:
                    self.pointslog.append([""] * 12)
                row = self.pointslog[index]
                row[first_col : first_col + len(row_values)] = row_values
        return response


@pytest.fixture
def stateful_graph(monkeypatch):
    graph = StatefulGraph(
        STUDENTS,
        [
            ["Date", "StudentID", "Class", "Att", "Bible", "BA", "MV", "Part", "B1", "B2", "B3", "Total"],
            ["2026-03-01", "S1", "Trek", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
    )
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        main.httpx, "AsyncClient", lambda *a, **kw: real_client(transport=httpx.MockTransport(graph.async_handler))
    )
    monkeypatch.setattr(main, "_pointslog_write_lock", asyncio.Lock())
    return graph


@pytest.mark.anyio
async def test_concurrent_score_updates_on_same_row_are_not_lost(stateful_graph):
    def update(**fields):
        return main.NormalizedStudentUpdate(
            date="2026-03-01", class_name="Trek", student_name="Ann", student_id="S1", **fields
        )

    await asyncio.gather(
        main.apply_pointslog_update(update(attendance=1), "t", allow_name_lookup=False),
        main.apply_pointslog_update(update(bible=1), "t", allow_name_lookup=False),
    )
    assert stateful_graph.pointslog[1] == ["2026-03-01", "S1", "Trek", 1, 1, 0, 0, 0, 0, 0, 0, 20]


@pytest.mark.anyio
async def test_concurrent_class_population_does_not_overwrite_rows(stateful_graph):
    stateful_graph.pointslog = stateful_graph.pointslog[:1]

    async def populate(class_name):
        async with httpx.AsyncClient(timeout=main.HTTP_TIMEOUT) as graph_client:
            return await main.ensure_pointslog_rows_for_class(graph_client, {}, "2026-03-01", class_name)

    await asyncio.gather(populate("Trek"), populate("Cubbies"))
    keys = sorted((row[1], row[2]) for row in stateful_graph.pointslog[1:])
    assert keys == [("S1", "Trek"), ("S2", "Trek"), ("S3", "Cubbies")]


@pytest.mark.parametrize("trusted, expected", [(True, "203.0.113.9"), (False, "testclient")])
def test_client_ip_key_only_trusts_forwarded_for_behind_proxy(monkeypatch, trusted, expected):
    monkeypatch.setattr(main, "TRUST_PROXY_HEADERS", trusted)
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"1.2.3.4, 203.0.113.9")],
            "client": ("testclient", 50000),
        }
    )
    assert main.client_ip_key(request) == expected


def test_student_summary_groups_by_student_id(client, fake_graph):
    fake_graph.students = [["StudentID", "Name", "Class"], ["S1", "Sam", "Trek"], ["S2", "Sam", "Trek"]]
    fake_graph.pointslog = [
        ["Date", "StudentID", "Class", "Att", "Bible", "BA", "MV", "Part", "B1", "B2", "B3", "Total"],
        ["2026-03-01", "S1", "Trek", 0, 0, 0, 0, 0, 0, 0, 0, 10],
        ["2026-03-08", "S1", "Trek", 0, 0, 0, 0, 0, 0, 0, 0, 20],
        ["2026-03-01", "S2", "Trek", 0, 0, 0, 0, 0, 0, 0, 0, 5],
    ]
    response = client.get("/sheets/student-summary")
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["Trek"] == [
        {"student_id": "S1", "name": "Sam", "total_points": 30},
        {"student_id": "S2", "name": "Sam", "total_points": 5},
    ]


# ---------------------------------------------------------------- /auth/token


def test_auth_token_rate_limited(monkeypatch):
    async def no_user(_token):
        return {}

    monkeypatch.setattr(main, "fetch_signed_in_user", no_user)
    with TestClient(main.app) as test_client:
        codes = [test_client.post("/auth/token", json={"access_token": "x"}).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_auth_token_rejects_token_failing_signature_check(monkeypatch, entra_jwks):
    async def graph_user(_token):
        return {"id": "oid-1", "displayName": "Leader"}

    monkeypatch.setattr(main, "fetch_signed_in_user", graph_user)
    bad = jwt.encode(_entra_claims(tid="other"), _RSA_KEY, algorithm="RS256", headers={"kid": _KID})
    with TestClient(main.app) as test_client:
        response = test_client.post("/auth/token", json={"access_token": bad})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"


def test_auth_token_issues_session_for_valid_token(monkeypatch, entra_jwks):
    async def graph_user(_token):
        return {"id": "oid-1", "displayName": "Leader", "userPrincipalName": "leader@example.org"}

    async def authorized(_token, _user):
        return None

    monkeypatch.setattr(main, "fetch_signed_in_user", graph_user)
    monkeypatch.setattr(main, "ensure_user_is_authorized", authorized)
    with TestClient(main.app) as test_client:
        response = test_client.post("/auth/token", json={"access_token": _graph_style_token(_entra_claims())})
    assert response.status_code == 200, response.text
    session = response.json()["access_token"]
    payload = main.require_authenticated_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=session))
    assert payload["oid"] == "oid-1"


# ---------------------------------------------------------------- authorization policy


@pytest.mark.anyio
async def test_production_denies_when_no_authorization_check_configured(monkeypatch):
    monkeypatch.setattr(main, "IS_PRODUCTION", True)
    monkeypatch.setattr(main, "ENFORCE_GROUP_MEMBERSHIP", False)
    with pytest.raises(HTTPException) as exc:
        await main.ensure_user_group_access("token", {})
    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_production_denies_when_no_group_configured(monkeypatch):
    monkeypatch.setattr(main, "IS_PRODUCTION", True)
    monkeypatch.setattr(main, "ENFORCE_GROUP_MEMBERSHIP", True)
    monkeypatch.setattr(main, "ALLOWED_GROUP_ID", "")
    monkeypatch.setattr(main, "ALLOWED_GROUP_NAME", "")
    with pytest.raises(HTTPException) as exc:
        await main.ensure_user_group_access("token", {})
    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_group_check_error_denies_by_default(monkeypatch):
    async def boom(*_args):
        raise RuntimeError("graph down")

    monkeypatch.setattr(main, "ALLOWED_GROUP_ID", "")
    monkeypatch.setattr(main, "ALLOWED_GROUP_NAME", "AwanaPointsLogger")
    monkeypatch.setattr(main, "check_membership_by_group_name", boom)
    assert main.FAIL_OPEN_ON_GROUP_CHECK_ERROR is False
    with pytest.raises(HTTPException) as exc:
        await main.ensure_user_group_access("token", {})
    assert exc.value.status_code == 403
