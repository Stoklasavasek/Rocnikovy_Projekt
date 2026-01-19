# Docker Setup - Cross-Platform Guide

## Rychlý start (Mac / Linux / Windows)

```bash
docker-compose up -d
```

## Řešení problémů na Windows

### 1. Porty jsou obsazené
Pokud porty 8000 nebo 8001 jsou obsazené, změňte je v `docker-compose.yml`:
```yaml
ports:
  - "8002:8000"  # Místo 8000 použijte 8002
  - "8003:8001"  # Místo 8001 použijte 8003
```

### 2. Problémy s volumes (cesty)
Windows používá jiný formát cest. Pokud máte problémy:
- Ujistěte se, že Docker Desktop běží
- Zkontrolujte File Sharing v Docker Desktop Settings
- Použijte absolutní cesty nebo WSL2

### 3. Oprávnění
Pokud máte problémy s oprávněními:
```bash
# V PowerShell (jako administrátor)
icacls "C:\cesta\k\projektu" /grant Everyone:F /T
```

### 4. Rebuild image
Pokud se změny neprojevují:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 5. Kontrola logů
```bash
docker-compose logs -f web
docker-compose logs -f db
```

## Optimalizace

- `.dockerignore` - zrychluje build
- Named volumes místo bind mounts (pro produkci)
- Multi-stage build (pro menší image)

