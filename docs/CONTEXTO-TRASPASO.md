# Contexto del proyecto — traspaso a otra sesión

Estado al 2026-08-07. Documento autocontenido: no hace falta el historial previo.

---

## 1. El trabajo práctico

**Nombre:** Optimización de la Ventana de Siembra a partir de Simulación de Operaciones Agrícolas.
Materia de Simulación, carrera de Ingeniería en Sistemas (UTN Rosario).

**Problema.** La ventana de siembra ideal en la pampa húmeda dura pocas semanas. Las interrupciones —fallas mecánicas de los tractores, desabastecimiento de insumos en el lote, eventos climáticos severos— penalizan fuertemente el rinde futuro del cultivo.

**Objetivo.** Dimensionar la maquinaria agrícola y la logística de apoyo (camiones tolva, acoplados tanque) para que la labor termine dentro de la ventana agronómica óptima, minimizando a la vez el riesgo productivo y la capacidad ociosa de los equipos contratados.

**Metodología.** Modelo híbrido: eventos discretos (ciclo de siembra, recarga y fallas en bucle) acoplado a dinámica de sistemas (humedad del perfil y evapotranspiración continuas). Cuando la lluvia satura el suelo se dispara una variable de control que detiene las máquinas hasta que el terreno "da piso".

**Alcance real: el modelo cubre el proceso productivo integrado — siembra + crecimiento + cosecha.** No es solo siembra.

**Entregables esperados.**
1. Curvas de probabilidad de terminar la siembra dentro de la ventana objetivo (ej. antes del 15 de noviembre) bajo distintos escenarios climáticos históricos.
2. Cuantificación de los cuellos de botella logísticos (tiempo de máquina parada esperando recarga).
3. Análisis financiero de trade-off: costo de alquiler de maquinaria extra contra beneficio de evitar pérdidas de rendimiento.

---

## 2. Entorno

- **SO:** Ubuntu 26.04 (GNOME sobre Wayland). **AnyLogic 8.9.9 Personal Learning Edition** instalado en `/home/renaiss/Descargas/anylogic`.
- **Problema conocido:** en la sesión GNOME/Wayland, AnyLogic (SWT) no permite arrastrar bloques de la paleta al canvas, y los campos de texto tienen retardo y pierden caracteres (culpa de `ibus-daemon`).
- **Solución que funciona:** iniciar sesión en **Xfce** (instalado con `sudo apt install xfce4`, manteniendo `gdm3` como gestor). Ahí el drag-and-drop anda bien.
- **Lanzadores creados** en la carpeta de instalación:
  - `start-anylogic-fixed.sh` — evita IBus (`GTK_IM_MODULE=xim`), arregla el tipeo.
  - `anylogic-xephyr.sh` — abre AnyLogic dentro de un servidor X anidado sin cerrar sesión. Funciona pero **quedó sin resolver una corrupción visual al hacer scroll**.
  - Acceso directo en `~/Escritorio/anylogic.desktop`, con acción de clic derecho para abrir sin Xephyr.
- Ubuntu 26.04 **no ofrece sesión Xorg** en GDM (GNOME la eliminó); por eso no aparece el engranaje con esa opción.

---

## 3. Archivos

| Qué | Dónde |
|---|---|
| Modelo | `/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp` |
| Respaldos fechados | `.../Harvest Simulator/backups/` |
| Plan de migración | `.../docs/superpowers/plans/2026-08-06-migracion-fluid-library.md` |
| Este documento | `.../docs/CONTEXTO-TRASPASO.md` |

La carpeta del modelo es un repositorio git.

El modelo **parte del ejemplo oficial "Harvest Simulator" de AnyLogic** (cosechadora + carro tolva + camión + silo), que se descargó del Cloud y se fue transformando.

**Agentes:** `Main`, `Combine`, `Cart`, `Truck` (4 de los 10 que permite PLE).

---

## 4. Lo más importante: la Fluid Library fue eliminada

**Por qué.** PLE limita el tiempo simulado a **5 horas en todas las librerías excepto la Process Modeling Library**. El modelo necesita semanas y años. La Fluid Library era incompatible de raíz.

**Qué se hizo.** Se borraron 12 bloques (`Tank`, `FluidEnter`, `FluidExit`, `FluidSource`, `Pipeline`), 8 conectores, y —crítico— el bloque `<RequiredLibraryReference>` del `.alp`, porque borrar los bloques del diagrama no alcanza para levantar el tope.

**Con qué se reemplazó.** Cada recipiente tiene ahora tres variables y una función:

```java
// actualizarNivel() en Combine, Cart y Truck
double dt = time() - tUltimo;
double bruto = nivel + tasaActual * dt;
if ( bruto > Capacity ) { main.masaDescartada += bruto - Capacity; bruto = Capacity; }
if ( bruto < 0 )        { main.masaInventada  += -bruto;           bruto = 0; }
nivel = bruto;
tUltimo = time();
```

**Convención de tasas:** `tasaActual` se expresa en unidades por **unidad de tiempo del modelo**. Los parámetros de tasa vienen en `PER_SECOND`, así que se convierten con `UnloadingRate / second()`.

**Eventos de nivel:** las transiciones que antes disparaban con mensajes `FULL`/`EMPTY` de los tanques pasaron a **timeout** con unidad SECOND:

```java
// llenado:  tasaActual > 0 ? ( ( Capacity - nivel ) / tasaActual ) / second() : 1e12
// vaciado:  tasaActual < 0 ? ( nivel / -tasaActual ) / second() : 1e12
```

Son cinco: `Cart.Full`, `Cart.trBecameEmpty`, `Combine.Full`, `Truck.transition5`, `Truck.transition3`.

**El silo** vive en Main como `nivelSilo` / `tasaSilo` / `tUltimoSilo` + `actualizarSilo()`, alimentado desde `Truck.Unloading`. Su dibujo ya existía en Main (grupo con rectángulo `tankBar` y polilínea `pipe`); solo se reapuntaron las expresiones.

---

## 5. Aprendizajes técnicos verificados (no repetir estos errores)

Todos contradicen algún supuesto razonable y cada uno costó al menos una corrida fallida.

1. **`Transition.restart()` no existe** en 8.9.9. Verificado con `javap` sobre `com.anylogic.engine.TransitionTimeout`. La API es `start()` y `cancel()`; `start()` reevalúa el timeout y reprograma.
2. **Las transiciones de salida de un estado se activan DESPUÉS de su entry action.** Consecuencias: (a) si el entry fija la tasa, el timeout ya se evalúa con el valor nuevo y no hace falta reprogramar; (b) llamar `cancel()` en el entry del propio estado origen tira `RuntimeException: a statechart transition being deactivated is not active`.
3. **Nunca reprogramar en un exit action:** la transición puede ser justamente la que está disparando.
4. Solo se reprograma cuando la tasa cambia en un estado **interno** y la transición cuelga de un compuesto **ancestro** ya activo. Quedan exactamente dos casos en el modelo: `Cart.trBecameEmpty` (en el entry de `Unloading`) y `Truck.transition5` (en el entry de `Loading`), ambos con guarda `if ( inState( ... ) ) { T.cancel(); T.start(); }`.
5. **`infinity()` no está disponible.** Se usa el literal `1e12`.
6. **Los objetos embebidos pisan los parámetros del tipo de agente.** Cambiar el default del tipo `Truck` no tiene efecto si la instancia `truck` en Main define su propio `Capacity`. Esto causó un diagnóstico equivocado durante horas. **Revisar siempre los overrides de instancia.**
7. **El `.alp` serializa los campos de todos los tipos de trigger**, no solo el activo. Una transición por `timeout` conserva su `<Condition>` y su `<EqualsExpression>` viejos. Al auditar el cableado de mensajes hay que filtrar por `Trigger="message"`, si no da falsos positivos.
8. **La Fluid Library acoplaba por conexión de puertos, con independencia del statechart.** Un tanque se llenaba estuviera el agente en el estado que estuviera. Al migrar a variables, todo acople implícito hay que reponerlo como mensaje explícito. Faltaba `START_LOADING`: el camión nunca entraba en `Loading`, nunca cargaba, y el silo quedaba vacío.
9. **`triangular(min, max, moda)`** — ese es el orden real. `weibull` toma 3 argumentos; el orden no fue verificado.
10. **Verificar APIs con `javap`**, no de memoria: `/home/renaiss/Descargas/anylogic/jre/bin/javap -classpath /home/renaiss/Descargas/anylogic/plugins/com.anylogic.engine_8.9.9.*/com.anylogic.engine.jar <clase>`.
11. **El `.alp` es XML** y se puede editar con scripts de Python. Procedimiento seguro: copia de respaldo fechada → editar con reemplazos que aborten si el patrón no aparece exactamente una vez → validar con `xml.etree.ElementTree.parse`.
12. **Límites de PLE:** 10 tipos de agente, 200 bloques por tipo, 50.000 agentes dinámicos.

---

## 6. Calibración actual (verificada contra valores reales)

| Parámetro | Valor | Nota |
|---|---|---|
| Escala (`ScaleRuler`) | 100 px = 250 m → **2,5 m/px** | era 10 m; el lote medía 0,17 ha |
| Lote (`field`) | 520 × 320 px = 1300 × 800 m = **104 ha** | |
| `HarvestDensity` | 0,3 kg/m² (3 t/ha) | rinde típico de soja → **312 t por campaña** |
| Cosechadora: velocidad | 5,5 km/h | |
| Cosechadora: `RowWidth` | 3,6 px = **9 m** de plataforma | |
| Cosechadora: `Capacity` | 9.000 kg | se llena cada ~36 min |
| Cosechadora: `UnloadingRate` | 100 kg/s | |
| Carro: `Capacity` | 20.000 kg | |
| Carro: `UnloadingRate` | 150 kg/s | |
| Carro: velocidad | 15 km/h | **override de instancia**, estaba en 2 |
| Camión: `Capacity` | 50.000 kg | **override de instancia**, estaba en 2.500 |
| Camión: `UnloadingRate` | 100 kg/s | |
| Camión: velocidad | 5 km/h | sin revisar; depende de la distancia al acopio |
| `CapacidadSilo` | 312.000 | solo escala del dibujo |

Comprobación: `harvestRate = 1,53 m/s × 9 m × 0,3 kg/m² = 4,1 kg/s ≈ 15 t/h`; recorrido `104 ha ÷ 9 m = 115,6 km` a 5,5 km/h = **21 h de labor efectiva**, valor confirmado por la instrumentación (21,09 h medidas).

**Los offsets del carro** (`main.combine.getX() - 40`) se cambiaron a `- main.combine.RowWidth`; el 40 hardcodeado funcionaba solo porque `RowWidth` valía 40.

---

## 7. Ciclo de cultivo y velocidad de presentación

Statechart `cicloCultivo` en Main:

```
SinSembrar ──[condition siembraCompleta]──> Creciendo ──[timeout diasHastaMadurez]──> Maduro ──[timeout 0, siembraCompleta=false]──> SinSembrar
```

- `Main.onCompleted()` (que llama la cosechadora al terminar la pasada) pone `siembraCompleta = true`.
- La cosechadora arranca con la condición `!main.siembraCompleta` en `Parked → GoingToField`.
- `Creciendo` entry sortea `diasHastaMadurez = triangular( 90, 150, 120 )` y guarda `tInicioCrecimiento`.
- **Deuda semántica:** `siembraCompleta` hoy significa "la pasada terminó". Cuando se agregue la campaña de siembra habrá que revisar el nombre y probablemente separar en dos banderas, o mejor, usar `inState()` como única fuente de verdad.

**Velocidad de simulación controlada desde el statechart** (API verificada):
- `SinSembrar` entry: `getEngine().setRealTimeScale( 0.05 * day() );` — la máquina trabaja, se mira al detalle.
- `Creciendo` entry: `getEngine().setRealTimeScale( 1 * week() );` — la maduración son meses sin nada que ver.
- Requiere el experimento en modo *Real time with scale*.

---

## 8. Integridad: auditoría de conservación de masa

`Main.auditarMasa()`, llamada desde `onCompleted()` (una vez por campaña), verifica:

```
totalCosechado == combine.nivel + cart.nivel + truck.nivel + nivelSilo + masaDescartada − masaInventada
```

`masaDescartada` y `masaInventada` contabilizan lo que antes desaparecía en el `max(0, min(Capacity, ...))`: el recorte dejó de ser silencioso.

**Estado:** ambas quedaron en ~1e-7 (ruido de punto flotante). **No hay masa fabricada ni destruida.** Se llegó ahí corrigiendo:
- La cosechadora seguía cosechando con la tolva llena y la máquina detenida → `FullWaitCart` pone las tasas en cero.
- El acople cosechadora–carro no conservaba: se resolvió con **volcado por lote** (al acoplarse se mueve `min(tolva, espacio en el carro)` de una variable a la otra en el mismo instante) más **régimen de goteo** (mientras siguen acoplados el carro recibe exactamente `tasaCosecha`).

**Pendiente conocido:** queda una fuga **constante** de −2500, que era exactamente la capacidad vieja del camión. Aparece desde la primera campaña y no crece. Hipótesis a verificar: si tras el cambio a 50 t pasa a −50.000, el artefacto está atado a una carga de camión.

**Contadores adicionales:** `horasCosechando`, `horasDetenida`, `viajesCamion` en Main, más un `traceln` por viaje del camión con su carga y un resumen por campaña.

---

## 9. Última medición y qué falta verificar

Con el bug del camión de 2.500 kg todavía presente:

```
120 viajes × 2.500 kg = 300.000 kg
cosechando = 21,09 h | detenida = 61,44 h | uso = 25%
```

La campaña tardaba 82,5 h porque el camión hacía 120 viajes de ~41 min. **Ya se corrigieron los overrides de instancia (camión 50 t, carro 15 km/h) pero el modelo NO se volvió a correr.** Lo primero que hay que hacer es correr y mirar:

- `viajes camion` debería bajar a ~6-7.
- `uso` debería subir bien por encima del 25%.
- La `FUGA`: si pasa a −50.000, el artefacto es una carga de camión.

---

## 10. Hoja de ruta pendiente

En orden de valor recomendado:

1. **Verificar la corrida** tras la corrección de overrides (punto 9).
2. **Fallas de máquina.** Diseño listo, sin implementar. Tercer statechart paralelo en `Combine` (junto a `tankControl` y `moveControl`): `Operativa ──[timeout horasHastaFalla]──> Reparando ──[timeout duracionReparacion]──> Operativa`. El reloj de desgaste se consume **solo mientras la máquina trabaja**, acoplado a `MoveHarvesting` con el mismo patrón que los niveles, y el timeout se expresa `inState( MoveHarvesting ) ? horasHastaFalla : 1e12`. **Detalle de orden importante:** el `STOP` lo manda `Reparando` al entrar, no la transición de falla, para que el rearmado guardado de `MoveHarvesting` se saltee solo y no haya `cancel()` sobre una transición que está disparando.
   - **Distribución:** exponencial con MTBF en **horas de operación** (justificable por superposición de procesos de falla, teorema de Drenick). Weibull con β>1 solo si se declara explícitamente el supuesto de reparación perfecta; para desgaste acumulado real el modelo correcto sería un proceso de Poisson no homogéneo con ley de potencia.
   - **Parámetros:** MTBF del orden de 20-40 h de operación (estudios de cosechadoras reportan MTBF por subsistema de 15 a 72 h; referencia oficial: ASABE D497.7). Reparación asimétrica a derecha, ej. `triangular(0.5, 8, 2)` horas. Costo = fijo + horario.
   - **Criterio de calibración:** apuntar a 0,5–3 fallas esperadas por campaña (`horas_campaña / MTBF`).
3. **Tabla climática** con esquema `fecha | lluvia_mm | tmax | tmin` en la base interna del modelo, cargada primero con datos sintéticos. Habilita el entregable 1 sin bloquear el desarrollo.
4. **Clima.** Reemplazar el timeout fijo de `Creciendo` por acumulación de **grados-día** (`Creciendo → Maduro` pasa a condition `gdd >= gddObjetivo`), de modo que el clima determine la duración del ciclo. En paralelo, stock de humedad de suelo con `daPiso = humedadSuelo < umbral`, reutilizando el par de mensajes `STOP`/`RESUME` que ya existe.
5. **Crecimiento visual.** El cultivo ya está dibujado: una figura replicada `rectangle3` en Main con `ReplicationCode = Xunits.length`. Solo falta ligar `ZHeightCode = progresoCultivo() * alturaMaxPlanta`, con `progresoCultivo()` calculado desde `tInicioCrecimiento` (ya creada) y `diasHastaMadurez`. **No crear un agente por planta**, sería un desperdicio y consume el cupo de tipos de agente.
6. **Campaña de siembra.** Reusar el patrón de recipientes con el flujo invertido (la semilla sale de la sembradora hacia el lote y los camiones la reponen). Conviene **una sola clase de máquina parametrizada** por modo (siembra/cosecha) en vez de duplicar, por el límite de 10 tipos de agente.
7. **Acople de rinde:** `rindeEfectivo = rindePotencial * penalizacionPorFecha( fechaSiembra )`, con la curva armada como lookup table a partir de datos de INTA de fecha de siembra contra rendimiento. Sin este acople, siembra y cosecha son dos simulaciones pegadas y el modelo no puede responder su propia pregunta.
8. **Monte Carlo** (Parameter Variation, animación apagada), una réplica por campaña climática histórica → las curvas de probabilidad del entregable 1.
9. Contadores de ocio para carro y camión (solo está hecho el de la cosechadora).

---

## 11. Fuentes de datos identificadas

- **Clima:** INTA SIGA y red RIAN (series históricas); CONAE, mapas de humedad de suelo integrado por satélite SAOCOM; BHOA (Balance Hídrico Operativo Agrícola, SMN + INTA + FAUBA).
- **Progreso de siembra y cosecha:** Bolsa de Cereales de Buenos Aires, "Panorama Agrícola Semanal" (15 zonas); Bolsa de Comercio de Rosario, estimaciones GEA.
- **Precios** para el análisis financiero: series históricas de pizarra (consiagro.com.ar).
- **Confiabilidad de maquinaria:** ASABE D497.7 "Agricultural Machinery Management Data".
- **Modelos de referencia en AnyLogic Cloud:** "Harvest Simulator" (el original de este modelo), "Farm Model", "Farm to Mill".

---

## 12. Preferencias de trabajo observadas

- Prefiere que los cambios se apliquen directamente sobre el `.alp` cuando son mecánicos, y guía en el IDE cuando hay que dibujar elementos nuevos de statechart.
- Pide análisis previo antes de implementar cuando hay una decisión de modelado de por medio (ej. eligió analizar la distribución de fallas antes de codificarla).
- Corrige activamente los supuestos: conviene verificar los valores contra el archivo antes de razonar sobre ellos.
