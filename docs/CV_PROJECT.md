# Ficha de CV y entrevista — VisionOps

## Bullet para el CV

> Implementé analítica visual multicloud orientada a privacidad, con eventos anónimos, ventanas temporales, alertas de ocupación e ingesta bulk observable.

Añade una cifra solamente después de ejecutar `scripts/generate_load.py` y `scripts/run_scale.py` en la máquina que declararás. Ejemplo válido: “validado localmente con 100 000 registros; procesamiento streaming y checksum por partición”.

## Complejidad que debes explicar

Procesa eventos fuera de orden sin almacenar rostros, aplica umbrales por zona y separa evidencia operativa de cualquier dato identificable.

El reto no es nombrar muchos servicios. Es mantener el mismo contrato de dominio, seguridad, idempotencia, observabilidad y recuperación en tres implementaciones cloud diferentes.

## Guion de 60 segundos

1. **Problema:** procesa detecciones y entrega una salida consumible, no sólo un notebook.
2. **Diseño portable:** el dominio y los contratos no importan SDKs de nube; los adaptadores cambian por proveedor.
3. **Escala:** NDJSON particionado, lectura streaming, API bulk idempotente, checksums y límites explícitos.
4. **Calidad:** pruebas unitarias, arquitectura validada, safe defaults de Terraform y CI en `develop`/`main`.
5. **Honestidad:** lo local está ejecutado; los recursos cloud permanecen `PLANNED` hasta contar con cuenta, credenciales, presupuesto y evidencia de despliegue.

## Preguntas difíciles

- **¿Ya está desplegado?** No. Está listo para preflight y plan; sólo la ruta local está verificada.
- **¿Un millón significa producción?** No por sí solo. Demuestra memoria acotada y repetibilidad; nube requiere prueba distribuida y SLO medido.
- **¿Por qué tres nubes?** Para mostrar traducción arquitectónica y evitar acoplar el dominio; no porque operar tres proveedores siempre sea la decisión más barata.
- **¿Qué mejorarías en producción?** Autenticación OIDC, WAF/API gateway, cola administrada, object storage, autoscaling, tracing, alarmas y prueba de recuperación.

## Cifra verificada que sí puedes mencionar

En la máquina documentada se procesaron 100 000 registros a 111,793 registros/s y se enviaron por HTTP bulk a 23,797 registros/s. Di siempre ‘prueba local sintética’ y enlaza `docs/evidence/local-100k.json`; no lo presentes como benchmark de nube.
