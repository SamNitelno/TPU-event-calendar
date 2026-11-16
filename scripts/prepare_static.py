"""Copy the Vite build to Vercel's native public directory after building.

The original web/dist remains available to FastAPI for SPA navigation fallbacks.
Only generated files are written; never clear an arbitrary deployment directory.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    dist = ROOT / "web" / "dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("Build web/dist first: npm --prefix web run build")
    shutil.copytree(dist, ROOT / "public", dirs_exist_ok=True)


if __name__ == "__main__":
    main()
