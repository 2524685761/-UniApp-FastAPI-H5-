import os
from pathlib import Path


MODEL_ID = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cache_dir = os.getenv("HF_HOME") or str(root / "model_cache" / "huggingface")

    # Ensure persistent cache directory exists (survives reboot)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    # Force online mode for the download step (we'll enable offline at runtime via config.local.txt)
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)

    try:
        from huggingface_hub import snapshot_download
    except Exception as e:
        raise SystemExit(
            "Missing dependency: huggingface_hub. Install it with:\n"
            "  pip install -U huggingface_hub\n"
            f"Original error: {e}"
        )

    print(f"[cache] HF_HOME={cache_dir}")
    print(f"[cache] Downloading {MODEL_ID} ... (first time may take a while)")

    snapshot_path = snapshot_download(
        repo_id=MODEL_ID,
        cache_dir=cache_dir,
        # No symlinks on Windows by default
        local_dir_use_symlinks=False,
    )

    print(f"[cache] Done. Snapshot stored at: {snapshot_path}")
    print("[cache] You can now run backend with HF_HUB_OFFLINE=true / TRANSFORMERS_OFFLINE=true")


if __name__ == "__main__":
    main()

