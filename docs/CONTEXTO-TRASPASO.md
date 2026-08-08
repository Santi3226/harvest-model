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

> **Hay dos máquinas.** Este documento se escribió en la de Ubuntu. Verificá en qué entorno estás antes de razonar sobre rutas: las de la sección 3 y el `javap` del aprendizaje 10 son de Linux y no existen en Windows.

### Windows (agregado 2026-08-07)

- **SO:** Windows 11 Pro. AnyLogic 8.9.9 PLE en `C:\Program Files\AnyLogic 8.9 Personal Learning Edition\`.
- **Modelo:** `C:\Users\Santiago\Models\Optimización de la Ventana de Siembra\` (la carpeta **no** se llama `Harvest Simulator`).
- **Workspace:** `C:\Users\Santiago\.AnyLogicPLE\Workspace8.8\Optimización de la Ventana de Siembra\`. Los `.java` de `src.generated\` son **stubs** de autocompletado (todo lanza `UnsupportedOperationException`): sirven para verificar nombres de estados y campos `Statechart`, no para leer lógica.
- **`javap`:** `C:\Program Files\AnyLogic 8.9 Personal Learning Edition\jre\bin\javap.exe -classpath "C:\Program Files\AnyLogic 8.9 Personal Learning Edition\plugins\com.anylogic.engine_8.9.9.202607020720\com.anylogic.engine.jar" <clase>`. Algunas clases (`UtilitiesRandom`) no están en ese jar; para esas, armar el classpath desde el `.classpath` del proyecto del workspace.
- **Se puede editar el `.alp` con AnyLogic abierto:** detecta el cambio externo y pide confirmación para recargar el modelo. No hace falta cerrarlo. Aun así conviene mirar el `.alp.autosave` antes de editar: si es más nuevo que el `.alp`, AnyLogic tiene estado en memoria sin volcar. Comparar los `<Id>` de ambos alcanza para saber si la diferencia es semántica o solo formato (AnyLogic re-serializa con su propia indentación y orden dentro de `<Variables>`).
- Sin sesión de AnyLogic abierta el archivo no queda bloqueado; igual conviene respaldo fechado antes de cada edición.

### Ubuntu

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

| Qué | Dónde (Ubuntu) | Dónde (Windows) |
|---|---|---|
| Modelo | `/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp` | `C:\Users\Santiago\Models\Optimización de la Ventana de Siembra\Optimización de la Ventana de Siembra.alp` |
| Respaldos fechados | `.../Harvest Simulator/backups/` | `...\Optimización de la Ventana de Siembra\backups\` |
| Plan de migración | `.../docs/superpowers/plans/2026-08-06-migracion-fluid-library.md` | ídem, relativo a la carpeta del modelo |
| Este documento | `.../docs/CONTEXTO-TRASPASO.md` | ídem |

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
13. **Las transiciones por condición NO se re-evalúan cuando la variable la modifica otro agente.** AnyLogic las testea en momentos discretos, y uno garantizado es al entrar al estado de origen. Síntoma que costó una sesión: `Parked --[!main.siembraCompleta]--> GoingToField` disparaba en t=0 (porque al entrar a `Parked` la condición ya era verdadera) y **nunca más**, aunque `siembraCompleta` volviera a `false` 120 días después. La cosechadora quedaba estacionada para siempre. Solución: `Statechart.onChange()` (verificado con `javap`, es público) desde donde se modifica la variable. En el modelo hay dos: `combine.moveControl.onChange()` en la acción de `Maduro → SinSembrar`, y `cicloCultivo.onChange()` al final de `onCompleted()`. **Regla: toda condición que dependa de una variable de otro agente necesita su `onChange()` explícito.**
14. **`SelectionModeForSimultaneousEvents` está en LIFO**, y eso rompe handshakes de dos mensajes emitidos en el mismo instante: el segundo enviado se procesa primero. Si el receptor todavía no está en el estado que escucha ese mensaje, **el mensaje se descarta en silencio** (una transición por mensaje no encola: si el estado no está activo, se pierde). Ver sección 8 para el caso concreto que fabricó 150 t de grano. **No cambiar a FIFO como arreglo**: sirve para confirmar un diagnóstico, pero tapa el handshake perdido y mueve el comportamiento de todo lo demás.
15. **Validar que el XML parsea no alcanza** (complemento del aprendizaje 11). Un script previo insertó variables dentro de `<Variables>` con indentación disparatada: el archivo parseaba, AnyLogic lo aceptaba y lo normalizaba al re-serializar. Es inofensivo pero produce diffs de git ilegibles y confunde el próximo diagnóstico. Verificar además el **padre** en el que se inserta y la indentación.
16. **`<Guard>` existe y es fácil pasarlo por alto.** `Cart.trImmedGotoUnloading` tiene `Trigger="timeout"` con timeout 0 **y** `<Guard>main.truck.atField()</Guard>`. Al auditar una transición hay que leer el `<Guard>` además del trigger, si no se razona sobre lógica que no es la real. Ojo: si la guarda es falsa al expirar el timeout, la transición no dispara y **no se reprograma** — por eso no conviene endurecer guardas sin verificar que exista otro camino de salida del estado (acá lo hay: `trTruckArrived` por mensaje).

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

### La FUGA: diagnosticada 2026-08-07

**La hipótesis de "una carga de camión" era incorrecta.** Tras corregir los overrides, la fuga pasó a **−150.000** (no a −50.000), idéntica en las dos campañas. Son **tres** cargas de camión, y el signo importa: `enSistema` > `cosechado`, así que la masa se **fabrica**, no se pierde.

**Cómo se identificó.** Por los intervalos entre viajes de la campaña 1. A 4,1 kg/s de tasa de cosecha, juntar 50.000 kg lleva 3,4 h. Los viajes 3, 6 y 9 llegaron **39 minutos** después del anterior con carga al 100%: imposible. La campaña 2 no tiene ningún gap de 39 min (todos entre 2,9 y 4,5 h) y por eso la fuga no creció. Reconciliación: campaña 1 = 6 viajes reales × 50.000 + ~13.200 en tolvas = 313.200 = `totalCosechado`, más 3 viajes fantasma × 50.000 = 150.000 fabricados.

**Mecanismo (carrera perdida por LIFO, ver aprendizaje 14).** Con el carro vacío en `WaitTruck` y el camión en `WaitCart`:

1. `trImmedGotoUnloading` (timeout 0, guarda `main.truck.atField()` verdadera) mete al carro en `Unloading`.
2. El entry de `Cart.Unloading` envía `START_LOADING`, fija `tasaActual = -150 kg/s` y rearma `trBecameEmpty` con timeout `nivel / 150` = **0**, porque el carro está vacío.
3. `trBecameEmpty` dispara en el mismo instante: el carro sale de `AtUnloading` y envía `FINISHED_LOADING`.
4. **LIFO:** `FINISHED_LOADING` se procesa primero, llega al camión todavía en `WaitCart`, no hay transición que lo escuche → se descarta.
5. Después llega `START_LOADING` → el camión entra a `Loading` con `tasaActual = +150 kg/s` y `transition5` rearmada a `(50.000 − nivel)/150 ≈ 333 s`.
6. Nadie está descargando. El camión se llena **de la nada** en 333 s y se va al silo con 50.000 kg inexistentes.

Cronómetro: 333 s de llenado + 500 s de descarga (50.000 ÷ 100 kg/s) + los dos viajes ≈ 39 min. Coincide.

`masaInventada` no lo detectó porque ese contador solo salta cuando un nivel se iría a **negativo**; acá la masa se crea en positivo sin tocar ningún clamp.

**Mitigación aplicada** (`backups/2026-08-07-pre-conservacion-camion.alp`): el entry de `Truck.Loading` ya no latchea la tasa, la deriva del estado real del carro:

```java
tasaActual = main.cart.inState( Cart.Unloading ) ? main.cart.UnloadingRate / second() : 0;
```

Un `FINISHED_LOADING` perdido ya no puede dejar al camión acumulando de la nada.

**Esa mitigación cortó la fabricación pero abrió el bug espejo**, confirmado en la corrida siguiente: la fuga cambió de signo a **+20.000**, exactamente la capacidad del carro. Una carga completa de carro drenando contra un camión que quedó en `Loading` con tasa 0.

> **Corrección importante para no confiarse:** se había predicho que esa pérdida quedaría registrada en `masaInventada`. **No queda.** Ese contador solo salta cuando un nivel se iría por debajo de cero, y acá el carro baja de 20.000 a 0 legítimamente. `masaInventada` y `masaDescartada` **detectan** el desbalance por agregado pero **no lo localizan**, y hay pérdidas que no tocan ningún clamp. Para localizar haría falta un libro mayor por recipiente (entró / salió).

**Arreglo aplicado** (`backups/2026-08-07-pre-tasas-apareadas.alp`). La causa de fondo era que **las tasas se latchean al entrar al estado y nadie las re-evalúa cuando el otro agente cambia de estado**. El eslabón cosechadora→carro nunca tuvo el problema porque la cosechadora fija **las dos** tasas (ver entry/exit de `Combine.WithCart`). Se portó ese patrón: ahora `Cart.Unloading` fija también la del camión, al entrar y al salir.

Dos detalles del arreglo, ambos deliberados:
- **`main.truck.transition5` se rearma solo desde el entry, nunca desde el exit.** Si el carro sale *porque* el camión se llenó (`transition5` → `TRUCK_DEPARTED` → `trTruckDeparted`), rearmar en el exit cancelaría la transición que está disparando → `RuntimeException` del aprendizaje 2.
- Como consecuencia, `transition5` puede disparar con el camión parcialmente cargado. **No viola conservación**, pero puede generar viajes con carga parcial. Si aparecen cargas al 60-80% en el log, es esto y no un bug de masa.

La guarda de `Truck.Loading` se dejó puesta como respaldo: es consistente con el nuevo esquema y cubre el caso de que el camión entre a `Loading` sin que el carro esté descargando.

### ✅ VERIFICADO — la cadena conserva masa (corrida 3, 2026-08-07)

```
Campaña 1: cosechado=313.199,9999999996  enSistema=313.200,00000000186  FUGA=-8,4e-11  (-2,7e-14 %)
Campaña 2: cosechado=626.400,000000174   enSistema=626.400,00000014     FUGA=+2,7e-10  (+4,2e-14 %)
```

Catorce órdenes de magnitud por debajo de lo relevante: es ruido de punto flotante, no un desbalance. **La cadena campo → cosechadora → carro → camión → silo conserva masa en las dos campañas.**

El efecto lateral que se temía (viajes con carga parcial por no rearmar `transition5` en el exit) **no se materializó**: los 12 viajes salieron al 100%. Si en calibraciones futuras aparecen cargas parciales, revisar esto antes de sospechar de la masa.

**No se aplicó el cambio a `trImmedGotoUnloading`** que se había propuesto (timeout `nivel > 0 ? 0 : 1e12`): al descubrir que la transición ya tiene `<Guard>`, endurecerla arriesga dejar al carro varado en `WaitTruck`, porque una guarda falsa al expirar el timeout no se reprograma (aprendizaje 16).

**Contadores adicionales:** `horasCosechando`, `horasDetenida`, `viajesCamion` en Main, más un `traceln` por viaje del camión con su carga y un resumen por campaña.

---

## 9. Última medición (2026-08-07, tras corregir overrides)

Corrida de dos campañas. **Los overrides de instancia eran el cuello de botella y quedó demostrado:**

| Métrica | Antes | Después |
|---|---|---|
| Viajes de camión (campaña 1) | 120 × 2.500 kg | **9** × 50.000 kg |
| Uso de la cosechadora | 25% | **91%** |
| Labor efectiva | 21,09 h | 21,09 h (sin cambios, como se esperaba) |
| Detenida | 61,44 h | **1,89 h** |

```
Corrida 1 (solo overrides corregidos):
  Campaña 1: cosechando=21,09 h | detenida=1,89 h  | uso=91% | viajes=9
             FUGA = -150.000  <- 3 viajes fantasma, ver seccion 8
  Campaña 2: detenida=2631,60 h | uso=1%           <- bug de la metrica

Corrida 2 (+ guarda de Truck.Loading, + reinicio de tUltimoEstado):
  Campaña 1: cosechando=21,09 h | detenida=1,82 h  | uso=92% | viajes=5
  Campaña 2: cosechando=42,18 h | detenida=3,57 h  | uso=92% | viajes=11
             FUGA = +20.000  <- cambio de signo: bug espejo, ver seccion 8
  Gaps entre viajes: 2,89 / 5,75 / 4,40 / 3,02 h -> NINGUNO de ~39 min. Fantasmas eliminados.

Corrida 3 (+ tasas apareadas en Cart.Unloading):   <-- ESTADO ACTUAL, todo verde
  Campaña 1: cosechando=21,09 h | detenida=1,89 h | uso=91% | viajes=6
  Campaña 2: cosechando=42,18 h | detenida=3,73 h | uso=91% | viajes=12 (6 en la campaña)
             FUGA = -8,4e-11 y +2,7e-10  -> ruido de punto flotante. CONSERVA.
  Las dos campañas idénticas: 21,09 h de labor, 91% de uso, 6 viajes cada una.
```

**Heurística de diagnóstico que funcionó tres veces:** cuando la `FUGA` no es ruido, su magnitud es un **múltiplo exacto de la capacidad de un recipiente**, y eso identifica el eslabón roto sin buscar a ciegas. −150.000 fueron 3 camiones (50.000); +20.000 fue 1 carro (20.000). Capacidades: 9.000 cosechadora / 20.000 carro / 50.000 camión.

### Segundo bug encontrado en esta corrida: la métrica de uso está mal

`detenida = 2631,6 h` en la campaña 2 son **109,65 días**: el período de maduración. `horasDetenida` acumula en el entry de `MoveHarvesting` todo el tiempo desde `tUltimoEstado`, así que los meses con la máquina en `Parked` se le imputan como tiempo parado. De ahí el `uso = 1%`.

Además los dos contadores son **acumulados de por vida**: `cosechando = 42,18 h` de la campaña 2 es 2 × 21,09. El bloque rotulado `CAMPANIA` reporta totales históricos, no la campaña.

**Corregido:** el entry de `Combine.GoingToField` ahora hace `tUltimoEstado = time();`, así la ventana de maduración deja de imputarse a la máquina. Verificado: `detenida` en la campaña 2 bajó de **2631,60 h a 3,57 h** y el uso quedó estable en 92% en ambas campañas.

**Pendiente:** reportar por campaña en vez de acumulado. Requiere variables nuevas en `Main` para la foto de los contadores al inicio de cada campaña, e imprimir el delta en `auditarMasa()`. Los números confiables hoy son los de la campaña 1.

---

## 10. Hoja de ruta pendiente

En orden de valor recomendado:

1. ~~Verificar la corrida tras la corrección de overrides~~ — **hecho 2026-08-07**, ver sección 9. Dejó dos pendientes concretos:
   - ~~Cerrar el eslabón carro→camión~~ — **aplicado y verificado 2026-08-07** (tasas apareadas en `Cart.Unloading`, sección 8).
   - ~~Verificar la `FUGA`~~ — **cerrada**: ruido de punto flotante en las dos campañas. **La base de logística ya es confiable**, se puede calibrar y medir sobre ella.
   - Queda abierto, menor: reportar los contadores **por campaña** en vez de acumulado (sección 9). Requiere variables nuevas en `Main` para la foto al inicio de cada campaña.
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
