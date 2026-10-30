# Optimización de la Ventana de Siembra

**Simulación híbrida en AnyLogic para dimensionar maquinaria agrícola y logística, y cerrar la siembra de soja antes del 15 de noviembre.**

Trabajo práctico de Simulación · UTN Rosario · AnyLogic 8.9.10 Personal Learning Edition

![Escena 3D del modelo: lote sembrado, cosechadora, carro, camión y silo](image.jpg)

## El problema

En la pampa húmeda la ventana de siembra dura pocas semanas. Sembrar tarde cuesta rinde, y contratar de más cuesta plata en máquinas paradas. La pregunta es **cuánta máquina y cuánta logística hacen falta para terminar a tiempo**, con el clima real de cada año y con roturas.

No alcanza con dividir hectáreas por capacidad horaria: el clima, las colas logísticas y la jornada legal se afectan entre sí. Por eso se simula.

## Qué modela

- **Ciclo del cultivo:** siembra → crecimiento → madurez → cosecha. Una corrida es una campaña completa, del 1/10 al 30/9.
- **Máquina con dos modos:** la misma máquina siembra a 7 km/h y cosecha a 5,5 km/h, y trabaja lote por lote (104,4 ha cada uno).
- **Logística:** un carro lleva semilla a la máquina y recoge el grano, un camión lo lleva al silo. Cada recipiente conserva la masa, y el modelo lo audita al cerrar la campaña.
- **Clima real:** 20 campañas (2005/06 a 2024/25) de NASA POWER. Un balance hídrico decide si el suelo "da piso"; con lluvia la máquina se frena.
- **Jornada legal:** 44 horas semanales por operario (Ley 26.727), con 1 a 3 turnos.
- **Fallas:** la máquina se rompe en horas de operación (MTBF de 100 h, supuesto) y espera la reparación.
- **Madurez por grados-día:** la meta se sortea por corrida (triangular 1.700 / 1.900 / 2.100), así que un año cálido madura antes y uno fresco después.

Es un modelo híbrido: **eventos discretos** (ciclo de siembra, recarga y descarga) y un **balance hídrico continuo**. Tiene 4 agentes (`Main`, `Combine`, `Cart` y `Truck`). La Fluid Library se eliminó, porque la edición PLE limita a 5 horas el tiempo simulado de toda librería salvo Process Modeling; los recipientes se integran por evento.

## Resultado (barrido del 30/10/2026)

Se compara el sistema **base** (12 lotes propios, 1 máquina) contra un **alternativo** (18 lotes con 6 arrendados, 2 máquinas), con 20 climas × 5 réplicas y las mismas semillas aleatorias en los dos sistemas.

|                                   | Base        | Alternativo   |
| --------------------------------- | ----------- | ------------- |
| Siembra terminada antes del 15/11 | 45%         | 95%           |
| Margen por campaña                | 940.130 US$ | 1.049.294 US$ |
| Margen por hectárea               | 750 US$     | 558 US$       |

La diferencia de margen a favor del alternativo es de 109.164 US$ por campaña (IC 95% por clima [100.121 ; 118.207]). Por hectárea gana el base. La ventaja del alternativo se anula con un costo fijo por tren de unos 229.000 US$, un precio de la soja de unos 250 US$/t o un arriendo de unos 20 qq/ha.

> **Límites.** Varios costos son supuestos sin fuente (listados en `herramientas/analizar_barrido.py` y en `docs/PLAN.md`). El exceso de fallas respecto de lo esperado (+8%) está marcado y sin explicar.

## Cómo correrlo

1. Instalar [AnyLogic 8.9.10 Personal Learning Edition](https://www.anylogic.com/downloads/) y abrir `Optimización de la Ventana de Siembra.alp`.
2. Elegir un experimento:

| Experimento           | Para qué sirve                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------------------- |
| `Simulation`          | Una corrida única, con animación. Termina al cerrar la cosecha                                  |
| `ParametersVariation` | El barrido de Monte Carlo (400 corridas). Escribe `resultados.csv`                              |
| `CompareRuns`         | Compara corridas en gráficos. La dirección web donde corre se imprime en la consola al lanzarlo |

3. Analizar el barrido (requiere Python 3, sin dependencias):

```bash
py herramientas/analizar_barrido.py
```

El barrido completo tiene que correrse con una sola versión de AnyLogic.

## Estructura del repositorio

| Ruta                                        | Contenido                                                                                                              |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `Optimización de la Ventana de Siembra.alp` | El modelo: un XML autocontenido con el código Java embebido                                                            |
| `herramientas/analizar_barrido.py`          | Analiza `resultados.csv`: margen de cada sistema, diferencia par a par con IC del 95%, siembra a tiempo y validaciones |
| `herramientas/clima_nasa.py`                | Baja el clima de NASA POWER y reescribe las series del modelo                                                          |
| `datos/`                                    | Serie climática de Rosario (NASA POWER, 2005–2025)                                                                     |
| `resultados.csv`, `salida/`                 | Resultados del barrido de 400 corridas y tabla para graficar                                                           |
| `docs/PLAN.md`                              | Plan de trabajo: decisiones, criterios y estado de cada paso                                                           |
| `docs/CAMBIOS-2026-10.md`                   | Cómo funciona el modelo de siembra, cosecha y clima anual                                                              |
| `docs/CONTEXTO-TRASPASO.md`                 | Estado del proyecto, calibración y aprendizajes de AnyLogic                                                            |
| `docs/ventana-siembra.html`                 | Explicación integral del modelo, con vocabulario, statecharts y variables                                              |
| `backups/`                                  | Copias fechadas del `.alp` anteriores a los últimos cambios por script                                                 |

## Para quien edita el modelo

- El código embebido está en español sin tildes (con ñ). Los documentos llevan tildes.
- Para tocar el `.alp` con scripts, seguir el procedimiento de `CLAUDE.md`: respaldo fechado, reemplazos que abortan si el patrón no aparece exactamente una vez y validación del XML.
- Antes de abrirlo en AnyLogic, cerrar el modelo sin guardar y reabrirlo, para no pisar cambios hechos por script.
