# Escala, API y evidencia — VisionOps

## Contrato demostrable

- Endpoint bulk: `POST /v1/detections/bulk` con `application/x-ndjson`.
- Idempotencia: encabezado obligatorio `Idempotency-Key`; el mismo lote no se contabiliza dos veces.
- Memoria acotada: generación, validación y agregación línea por línea; particiones de 50 000 registros por defecto.
- Perfiles: `smoke=1 000`, `medium=100 000`, `large=1 000 000`; `--rows` permite una cifra explícita.
- Evidencia: checksums SHA-256, manifiesto de particiones, tiempo, throughput local y dashboard HTML.
- Límites locales configurables: `BULK_MAX_RECORDS`, `BULK_MAX_BYTES` y `BULK_MAX_LINE_BYTES`.

## Ejecutar

```powershell
python scripts/generate_load.py --profile medium
python scripts/run_scale.py
python scripts/serve_api.py
# En otra terminal: genera y transmite por chunks
python scripts/generate_load.py --rows 100000 --output artifacts/api-load --api-url http://127.0.0.1:8000
# Prueba HTTP autocontenida, incluida la repetición idempotente
python scripts/benchmark_api.py --rows 100000
```

La API expone `/health/live`, `/health/ready`, `/v1/status` y `/metrics`. El dashboard queda en `artifacts/scale-report/dashboard.html`.

## Qué significa “masivo” aquí

El perfil de un millón prueba que el algoritmo no depende de cargar el dataset completo en RAM. El throughput publicado siempre debe acompañarse de máquina, fecha, cantidad y comando. No se extrapola una medición local como si fuera rendimiento de AWS, Azure o GCP.

## Modelo

No reentrena un modelo fundacional: usa adaptadores sustituibles y dobles locales deterministas. El repositorio distingue artefactos realmente entrenados en local de servicios administrados únicamente diseñados para despliegue posterior.
