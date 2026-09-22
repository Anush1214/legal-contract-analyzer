import sys
import subprocess
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent
    venv_uvicorn = root_dir / "venv" / "Scripts" / "uvicorn.exe"
    uvicorn_cmd = str(venv_uvicorn) if venv_uvicorn.exists() else "uvicorn"

    cmd = [
        uvicorn_cmd,
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
