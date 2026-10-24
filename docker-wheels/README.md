# Optional offline build cache

Normal Render builds download pinned Python packages. For a restricted local Docker builder, download the same verified wheels first:

```bash
python -m pip download --only-binary=:all: -r requirements-render.lock -d docker-wheels
docker build --build-arg SISA_OFFLINE_BUILD=1 -t sisa-platform .
```

Wheel files are local build outputs and must not be committed. Recheck versions and artifact integrity when refreshing this cache. No dependency verification is disabled.
