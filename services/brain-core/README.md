# brain-core setup

`brain-core` is validated against **Python 3.12**.

## Local bootstrap

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests/test_smoke.py tests/test_service_entrypoint.py -q
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000
```

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest tests/test_smoke.py tests/test_service_entrypoint.py -q
python -m pytest tests -q
python -m uvicorn src.main:app --reload --port 8000
```

## Notes

- Python 3.14 is not part of the supported local baseline for this service yet.
- If `.venv` points at an old Python path, delete it and recreate it with Python 3.12.
- CI uses Python 3.12 and `requirements.txt` as the source of truth.


## Recommended local check order

1. `python -m pytest tests/test_smoke.py tests/test_service_entrypoint.py -q`
2. `python -m uvicorn src.main:app --reload --port 8000`
3. `python -m pytest tests -q` only after the smoke path is stable on your machine
