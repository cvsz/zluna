# Development Guide: zluna

## 1. Local Environment Setup

1. **Clone the repository**:
   ```bash
   git clone git@github.com:cvsz/zluna.git
   cd zluna
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Install dependencies**:
   ```bash
   python3 -m pip install -r <(echo "pytest pytest-asyncio pytest-cov")
   ```

## 2. Running Locally

Start the realtime simulation server:
```bash
make run
# or: PYTHONPATH=src python3 src/app.py
```
Default bind is `http://127.0.0.1:9581`. Access the live Web HUD at `http://127.0.0.1:9581` or via Cloudflare Tunnel at `https://zluna.zeaz.dev`.

## 3. Running Test Suite

Execute all unit, integration, and enterprise tests:
```bash
make test
# or: PYTHONPATH=src pytest tests/ -v
```

## 4. Code Quality & Standards

- **Formatting & Style**: Python 3.12+ type hints, clean docstrings, snake_case function names.
- **Safety Boundary**: Strict adherence to synthetic dual-currency rules (`real_money=False`).
- **GPG Signing**: All commits pushed to `main` must be GPG signed (`git commit -S`).
