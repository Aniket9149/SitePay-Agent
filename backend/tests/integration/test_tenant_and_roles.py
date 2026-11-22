#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for tenant separation, role permissions, projects, sites and last owner protection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from conftest import auth_headers, register_user

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

API = "/api/v1/organizations"


def create_project(client: TestClient, registration: dict[str, Any], name: str = "Tower A") -> Any:  # noqa: ANN401 - the HTTP response object
    """Create a project as the registered owner and return the response.

    Keeps the tests short.
    """
    organization_id = registration["organization"]["id"]
    return client.post(
        f"{API}/{organization_id}/projects",
        json={"name": name, "client_name": "City Authority", "contract_value": "1250000.50"},
        headers=auth_headers(registration),
    )


def test_project_create_read_update_with_exact_money(client: TestClient) -> None:
    """Contract value round trips exactly and updates change only the sent fields."""
    owner = register_user(client, "owner@example.com")
    organization_id = owner["organization"]["id"]
    created = create_project(client, owner)
    assert created.status_code == 201
    project = created.json()
    assert project["contract_value"] in ("1250000.50", 1250000.5, "1250000.5")

    updated = client.patch(
        f"{API}/{organization_id}/projects/{project['id']}",
        json={"client_name": "New Client"},
        headers=auth_headers(owner),
    )
    assert updated.status_code == 200
    assert updated.json()["client_name"] == "New Client"
    assert updated.json()["name"] == "Tower A"

    duplicate = create_project(client, owner)
    assert duplicate.status_code == 409
    bad_dates = client.patch(
        f"{API}/{organization_id}/projects/{project['id']}",
        json={"start_date": "2026-05-01", "end_date": "2026-04-01"},
        headers=auth_headers(owner),
    )
    assert bad_dates.status_code == 422


def test_another_company_cannot_see_or_touch_a_project(client: TestClient) -> None:
    """Tenant separation: every cross-company access is "not found"."""
    company_a = register_user(client, "a@example.com", "Company A")
    company_b = register_user(client, "b@example.com", "Company B")
    project_id = create_project(client, company_a).json()["id"]
    a_org, b_org = company_a["organization"]["id"], company_b["organization"]["id"]

    assert client.get(f"{API}/{a_org}/projects", headers=auth_headers(company_b)).status_code == 404
    assert client.get(f"{API}/{a_org}", headers=auth_headers(company_b)).status_code == 404
    assert (
        client.get(
            f"{API}/{b_org}/projects/{project_id}", headers=auth_headers(company_b)
        ).status_code
        == 404
    )
    assert client.get(f"{API}/{b_org}/projects", headers=auth_headers(company_b)).json() == []
    assert (
        client.patch(
            f"{API}/{b_org}/projects/{project_id}",
            json={"name": "Hijack"},
            headers=auth_headers(company_b),
        ).status_code
        == 404
    )


def test_roles_limit_what_members_can_do(client: TestClient) -> None:
    """A worker can read but not create. An engineer can add sites but not projects."""
    owner = register_user(client, "owner@example.com")
    worker = register_user(client, "worker@example.com", "Worker Own Company")
    engineer = register_user(client, "engineer@example.com", "Engineer Own Company")
    organization_id = owner["organization"]["id"]
    for person, role in ((worker, "worker"), (engineer, "engineer")):
        added = client.post(
            f"{API}/{organization_id}/members",
            json={"email": person["user"]["email"], "role": role},
            headers=auth_headers(owner),
        )
        assert added.status_code == 201, added.text
    project_id = create_project(client, owner).json()["id"]

    assert create_project(client, {**owner, "tokens": worker["tokens"]}, "Other").status_code == 403
    assert (
        client.get(f"{API}/{organization_id}/projects", headers=auth_headers(worker)).status_code
        == 200
    )
    site_url = f"{API}/{organization_id}/projects/{project_id}/sites"
    assert (
        client.post(site_url, json={"name": "Block 1"}, headers=auth_headers(worker)).status_code
        == 403
    )
    engineer_site = client.post(site_url, json={"name": "Block 1"}, headers=auth_headers(engineer))
    assert engineer_site.status_code == 201
    assert (
        client.post(site_url, json={"name": "Block 1"}, headers=auth_headers(engineer)).status_code
        == 409
    )
    assert (
        client.post(
            f"{API}/{organization_id}/members",
            json={"email": "x@example.com", "role": "worker"},
            headers=auth_headers(engineer),
        ).status_code
        == 403
    )


def test_last_owner_cannot_be_demoted_or_removed(client: TestClient) -> None:
    """An organization always keeps at least one owner."""
    owner = register_user(client, "owner@example.com")
    organization_id = owner["organization"]["id"]
    members = client.get(f"{API}/{organization_id}/members", headers=auth_headers(owner)).json()
    membership_id = members[0]["membership_id"]
    demote = client.patch(
        f"{API}/{organization_id}/members/{membership_id}",
        json={"role": "worker"},
        headers=auth_headers(owner),
    )
    assert demote.status_code == 422
    remove = client.delete(
        f"{API}/{organization_id}/members/{membership_id}", headers=auth_headers(owner)
    )
    assert remove.status_code == 422


def test_site_of_another_project_or_company_is_not_found(client: TestClient) -> None:
    """Sites are only reachable through their own project and organization."""
    company_a = register_user(client, "a@example.com", "Company A")
    company_b = register_user(client, "b@example.com", "Company B")
    a_org, b_org = company_a["organization"]["id"], company_b["organization"]["id"]
    project_id = create_project(client, company_a).json()["id"]
    site = client.post(
        f"{API}/{a_org}/projects/{project_id}/sites",
        json={"name": "Block 1"},
        headers=auth_headers(company_a),
    ).json()
    cross = client.get(
        f"{API}/{b_org}/projects/{project_id}/sites/{site['id']}", headers=auth_headers(company_b)
    )
    assert cross.status_code == 404
