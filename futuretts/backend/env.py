import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    """
    Load KEY=VALUE lines into os.environ (does not override existing env vars).
    """
    try:
        if not path.exists() or not path.is_file():
            return
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        return


def load_local_env() -> None:
    root = Path(__file__).resolve().parents[1]
    load_env_file(root / ".env.local")
    load_env_file(root / "backend" / ".env.local")


# load on import
load_local_env()


