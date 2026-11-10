"""Раздача собранного фронтенда: страницы по прямой ссылке, файлы сборки, API не перекрывается."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.frontend import mount_frontend


@pytest.fixture
def site(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "assets" / "index-1a2b3c.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    mount_frontend(app, dist)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/event/12", "/submit", "/admin", "/admin/"])
def test_app_pages_open_by_direct_link(site, path):
    response = site.get(path)
    assert response.status_code == 200
    assert 'id="root"' in response.text


def test_build_files_are_served_and_assets_are_cached(site):
    script = site.get("/assets/index-1a2b3c.js")
    assert script.text == "console.log('app')"
    assert "immutable" in script.headers["cache-control"]
    icon = site.get("/favicon.svg")
    assert icon.text == "<svg/>"
    assert "cache-control" not in icon.headers


def test_api_is_not_shadowed_by_frontend(site):
    assert site.get("/api/ping").json() == {"ok": True}
    missing = site.get("/api/nope")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")


def test_files_outside_build_are_not_served(site):
    response = site.get("/..%2Fsecret.txt")
    assert "secret" not in response.text


def test_without_build_root_leads_to_api_docs(tmp_path):
    app = FastAPI()
    mount_frontend(app, tmp_path / "dist")
    response = TestClient(app).get("/", follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (307, "/docs")
