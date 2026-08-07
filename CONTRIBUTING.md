# Contribución y GitFlow

## Modelo de ramas

- `main`: releases estables y demostrables.
- `develop`: integración del siguiente incremento.
- `feature/<nombre-corto>`: cambio acotado creado desde `develop`.
- `release/<version>`: estabilización opcional antes de `main`.
- `hotfix/<nombre-corto>`: corrección urgente creada desde `main`.

## Recorrido de un cambio

```text
develop -> feature/* -> pull request -> develop -> release/* -> main
                                     hotfix/* -> main y develop
```

Las integraciones relevantes usan merge no fast-forward para que el historial
muestre el propósito de cada rama. No se realizan commits funcionales directos
en `main`.

## Requisitos del pull request

- pruebas locales correctas;
- diagramas regenerados y consistentes cuando cambia la arquitectura;
- `terraform fmt -check` y safe-default tests correctos cuando cambia IaC;
- documentación y evidencia actualizadas;
- ningún secreto, estado Terraform, credencial o dataset masivo versionado;
- dominio portable sin acoplamiento innecesario a un SDK cloud;
- afirmaciones cloud respaldadas por evidencia en `docs/evidence/` y con
  identificadores sensibles eliminados.

## Convención de commits

```text
feat(scope): nueva capacidad
fix(scope): corrección observable
test(scope): cobertura o prueba de regresión
docs(scope): documentación o diagramas
refactor(scope): cambio interno sin alterar el contrato
chore(scope): mantenimiento de herramientas o dependencias
```

Los mensajes deben explicar el cambio realizado. No se incluyen firmas de
asistentes, coautorías automáticas ni elementos decorativos.
