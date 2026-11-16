"""Check real frontend artifacts, SPA routes, API priority and deployment metadata."""

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app

ROOT = Path(__file__).resolve().parent.parent


def main():
    assert (ROOT / "public" / "index.html").is_file(), "Run scripts/prepare_static.py first"
    config = json.loads((ROOT / "vercel.json").read_text())
    assert config["framework"] == "fastapi"
    with TestClient(app) as client:
        for route in ["/", "/calendar", "/event/12", "/submit", "/guide", "/admin"]:
            response = client.get(route)
            assert response.status_code == 200 and 'id="root"' in response.text, route
            assert response.headers["cache-control"] == "no-cache"
        for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', response.text):
            result = client.get(asset)
            assert result.status_code == 200 and "immutable" in result.headers["cache-control"], asset
            assert (ROOT / "public" / asset.lstrip("/")).is_file()
        assert client.get("/api/missing").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api/admin/me").status_code == 401
    print("Deployment package checks passed")


if __name__ == "__main__":
    main()
