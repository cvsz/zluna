# Release Guide: zluna

## 1. Versioning Strategy

`zluna` uses [Semantic Versioning 2.0.0](https://semver.org/).
- Current Active Version: `v2.0.0`
- Major: Core engine, protocol, or state schema changes.
- Minor: New game implementations, marketing modules, or wallet chains.
- Patch: Bug fixes, UI improvements, and telemetry tweaks.

## 2. Release Checklist

1. **Test Verification**: Ensure `PYTHONPATH=src pytest tests/ -v` passes 100% (28/28 tests).
2. **Security Gates**: Verify zero secret files tracked (`.env` in `.gitignore`) and CodeQL passes.
3. **Changelog Update**: Add entries to `CHANGELOG.md` under the release version.
4. **Git Tagging**: Create a signed annotated tag:
   ```bash
   git tag -s v2.0.0 -m "Release v2.0.0: ZLUNA Enterprise Suite"
   git push origin v2.0.0
   ```
5. **Deployment Service**:
   ```bash
   systemctl --user restart zluna.service
   ```
6. **Live Ingress Verification**: Confirm `curl https://zluna.zeaz.dev/health` returns `HTTP 200 OK`.
