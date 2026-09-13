from typing import Any

from httpx import AsyncClient, Response


async def register_and_login(client: AsyncClient, email: str) -> str:
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Portfolio Tester",
            "password": "a-secure-test-password",
        },
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "a-secure-test-password"},
    )
    assert login.status_code == 200
    return str(login.json()["access_token"])


def auth_headers(token: str, organization_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if organization_id is not None:
        headers["X-Organization-ID"] = organization_id
    return headers


async def expect_created(response: Response) -> dict[str, Any]:
    assert response.status_code == 201, response.text
    return dict(response.json())


async def test_complete_property_leasing_workflow(client: AsyncClient) -> None:
    token = await register_and_login(client, "owner@example.com")
    me = await client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"

    organization = await expect_created(
        await client.post(
            "/api/v1/organizations",
            headers=auth_headers(token),
            json={"name": "Northstar Property Group"},
        )
    )
    organization_id = str(organization["id"])
    headers = auth_headers(token, organization_id)

    organizations = await client.get("/api/v1/organizations", headers=auth_headers(token))
    assert organizations.status_code == 200
    assert organizations.json()[0]["role"] == "owner"

    property_ = await expect_created(
        await client.post(
            "/api/v1/properties",
            headers=headers,
            json={
                "name": "Victoria Plaza",
                "address_line": "14 Market Street",
                "city": "Lagos",
                "country_code": "ng",
            },
        )
    )
    unit = await expect_created(
        await client.post(
            "/api/v1/properties/units",
            headers=headers,
            json={
                "property_id": property_["id"],
                "label": "Shop A-12",
                "bedrooms": 0,
                "monthly_rent": "350000.00",
                "currency": "ngn",
            },
        )
    )
    tenant = await expect_created(
        await client.post(
            "/api/v1/tenants",
            headers=headers,
            json={
                "first_name": "Ada",
                "last_name": "Okafor",
                "email": "ada@example.com",
            },
        )
    )
    lease_payload = {
        "unit_id": unit["id"],
        "tenant_id": tenant["id"],
        "starts_on": "2026-10-01",
        "ends_on": "2027-09-30",
        "monthly_rent": "350000.00",
        "deposit": "700000.00",
        "status": "active",
    }
    await expect_created(await client.post("/api/v1/leases", headers=headers, json=lease_payload))

    overlap = await client.post("/api/v1/leases", headers=headers, json=lease_payload)
    assert overlap.status_code == 409

    properties = await client.get("/api/v1/properties", headers=headers)
    units = await client.get("/api/v1/properties/units", headers=headers)
    tenants = await client.get("/api/v1/tenants", headers=headers)
    leases = await client.get("/api/v1/leases", headers=headers)
    assert [len(response.json()) for response in (properties, units, tenants, leases)] == [
        1,
        1,
        1,
        1,
    ]

    invitation = await client.post(
        "/api/v1/organizations/invitations",
        headers=headers,
        json={"email": "manager@example.com", "role": "manager"},
    )
    assert invitation.status_code == 202
    assert invitation.json()["role"] == "manager"


async def test_organization_boundary_rejects_an_outsider(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "boundary-owner@example.com")
    outsider_token = await register_and_login(client, "outsider@example.com")
    organization = await expect_created(
        await client.post(
            "/api/v1/organizations",
            headers=auth_headers(owner_token),
            json={"name": "Private Organization"},
        )
    )
    response = await client.get(
        "/api/v1/properties",
        headers=auth_headers(outsider_token, str(organization["id"])),
    )
    assert response.status_code == 403


async def test_duplicate_registration_is_rejected(client: AsyncClient) -> None:
    await register_and_login(client, "duplicate@example.com")
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "full_name": "Duplicate User",
            "password": "a-secure-test-password",
        },
    )
    assert response.status_code == 409
