# Contexto del proyecto — traspaso a otra sesión

Estado al 2026-10-05 (revisión contra el `.alp` de `main`, commit `7d49555`). Documento autocontenido: no hace falta el historial previo.

> **Entregable #1 cerrado (2026-08-11, rehecho 2026-08-27).** Clima histórico real acoplado, jornada legal modelada y Monte Carlo de 300 corridas: la curva de probabilidad y la respuesta de dimensionamiento están en la **sección 9 bis**.
>
> **Cambios del 2026-10-05:** el modelo ahora siembra de verdad (misma máquina, dos modos), el cultivo crece y se cosecha, con clima anual. Está explicado en [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md) y verificado con una corrida. **La tabla de la sección 9 bis es del modelo anterior y hay que rehacerla.**
>
> **Lo que falta** (detalle en la sección 10): siembra v2 con reabastecimiento de semilla, rehacer el barrido, roturas de máquina, acople térmico `gdd → Maduro`, cuellos de botella de carro y camión, y el análisis financiero con acople de rinde.

---

## 1. El trabajo práctico

**Nombre:** Optimización de la Ventana de Siembra a partir de Simulación de Operaciones Agrícolas.
Materia de Simulación, carrera de Ingeniería en Sistemas (UTN Rosario).

**Problema.** La ventana de siembra ideal en la pampa húmeda dura pocas semanas. Las interrupciones —fallas mecánicas de los tractores, desabastecimiento de insumos en el lote, eventos climáticos severos— penalizan fuertemente el rinde futuro del cultivo.

**Objetivo.** Dimensionar la maquinaria agrícola y la logística de apoyo (camiones tolva, acoplados tanque) para que la labor termine dentro de la ventana agronómica óptima, minimizando a la vez el riesgo productivo y la capacidad ociosa de los equipos contratados.

**Metodología.** Modelo híbrido: eventos discretos (ciclo de siembra, recarga y fallas en bucle) acoplado a dinámica de sistemas (humedad del perfil y evapotranspiración continuas). Cuando la lluvia satura el suelo se dispara una variable de control que detiene las máquinas hasta que el terreno "da piso".

**Alcance real: el modelo cubre el proceso productivo integrado — siembra + crecimiento + cosecha.** No es solo siembra.

**Resultados que el modelo tiene que poder mostrar.** Ojo: **no hay entregas por etapas.** La cursada tiene una sola presentación del trabajo completo. Esta lista son los resultados que esa presentación debe sostener, no hitos con fecha.
1. Curvas de probabilidad de terminar la siembra dentro de la ventana objetivo (ej. antes del 15 de noviembre) bajo distintos escenarios climáticos históricos.
2. Cuantificación de los cuellos de botella logísticos (tiempo de máquina parada esperando recarga).
3. Análisis financiero de trade-off: costo de alquiler de maquinaria extra contra beneficio de evitar pérdidas de rendimiento.

---

## 2. Entorno

> **Hay tres máquinas.** Este documento se escribió en la de Ubuntu. Verificá en qué entorno estás antes de razonar sobre rutas: las de la sección 3 y el `javap` del aprendizaje 10 son de una máquina en particular.

### Fedora (Luca, agregado 2026-10-05)

- **AnyLogic 8.9.9 PLE** en `/home/lucaolivieri/Downloads/anylogic` (`.eclipseproduct`: `version=8.9.9.202607020720`). Se actualizó encima de una 8.9.8, así que en `plugins/` conviven `com.anylogic.engine_8.9.8.*` y `com.anylogic.engine_8.9.9.*`. Para `javap`, usar el glob `com.anylogic.engine_8.9.9.*`: el glob amplio expande a dos jars.
- **Modelo:** `~/Desktop/facultad/simulacion/harvest-model` (clon del repositorio git). `~/Models` tiene otros modelos de la cursada, no este.

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
| Resultados del barrido | `.../resultados.csv` (versionado) | ídem |
| Modelos 3D del cultivo | `.../3d/low_poly_wheat.dae`, `.../3d/sketch.dae` | ídem |
| Explicación integral del modelo | `.../docs/ventana-siembra.html` | ídem |
| Respaldos fechados | `.../Harvest Simulator/backups/` | `...\Optimización de la Ventana de Siembra\backups\` |
| Plan de migración | `.../docs/superpowers/plans/2026-08-06-migracion-fluid-library.md` | ídem, relativo a la carpeta del modelo |
| Este documento | `.../docs/CONTEXTO-TRASPASO.md` | ídem |

La carpeta del modelo es un repositorio git (rama principal `main`). En Fedora el clon está en `~/Desktop/facultad/simulacion/harvest-model`.

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
10. **Verificar APIs con `javap`**, no de memoria: `/home/renaiss/Descargas/anylogic/jre/bin/javap -classpath /home/renaiss/Descargas/anylogic/plugins/com.anylogic.engine_8.9.9.*/com.anylogic.engine.jar <clase>`. Fijar la versión en el glob: si hay dos plugins del motor instalados, `com.anylogic.engine_*` rompe el classpath.
11. **El `.alp` es XML** y se puede editar con scripts de Python. Procedimiento seguro: copia de respaldo fechada → editar con reemplazos que aborten si el patrón no aparece exactamente una vez → validar con `xml.etree.ElementTree.parse`.
12. **Límites de PLE:** 10 tipos de agente, 200 bloques por tipo, 50.000 agentes dinámicos.
13. **Las transiciones por condición NO se re-evalúan cuando la variable la modifica otro agente.** AnyLogic las testea en momentos discretos, y uno garantizado es al entrar al estado de origen. Síntoma que costó una sesión: `Parked --[!main.siembraCompleta]--> GoingToField` disparaba en t=0 (porque al entrar a `Parked` la condición ya era verdadera) y **nunca más**, aunque `siembraCompleta` volviera a `false` 120 días después. La cosechadora quedaba estacionada para siempre. Solución: `Statechart.onChange()` (verificado con `javap`, es público) desde donde se modifica la variable. En el modelo hay dos: `combine.moveControl.onChange()` en la acción de `Maduro → SinSembrar`, y `cicloCultivo.onChange()` al final de `onCompleted()`. **Regla: toda condición que dependa de una variable de otro agente necesita su `onChange()` explícito.**
14. **`SelectionModeForSimultaneousEvents` está en LIFO**, y eso rompe handshakes de dos mensajes emitidos en el mismo instante: el segundo enviado se procesa primero. Si el receptor todavía no está en el estado que escucha ese mensaje, **el mensaje se descarta en silencio** (una transición por mensaje no encola: si el estado no está activo, se pierde). Ver sección 8 para el caso concreto que fabricó 150 t de grano. **No cambiar a FIFO como arreglo**: sirve para confirmar un diagnóstico, pero tapa el handshake perdido y mueve el comportamiento de todo lo demás.
15. **Validar que el XML parsea no alcanza** (complemento del aprendizaje 11). Un script previo insertó variables dentro de `<Variables>` con indentación disparatada: el archivo parseaba, AnyLogic lo aceptaba y lo normalizaba al re-serializar. Es inofensivo pero produce diffs de git ilegibles y confunde el próximo diagnóstico. Verificar además el **padre** en el que se inserta y la indentación.
16. **No usar `return` en acciones de transición ni de estado.** AnyLogic no las compila como métodos propios: las despacha desde uno compartido (`executeActionOf`, visible en cualquier stack trace). Un `return` sale del **despachador**, no de la acción, y saltea el rearmado de la autotransición. Síntoma real: un tick horario con `if ( horaTick % 24 != 0 ) return;` se disparó **una sola vez**, `diaCampania` quedó clavado en 0 y **400 corridas de barrido devolvieron 0**. Envolver en `if` en vez de salir temprano. Dentro de una `Function` el `return` se usa normalmente.
17. **La lista de parámetros de un experimento Parameter Variation se congela al crearlo.** Los parámetros agregados a `Main` después **no aparecen** y las corridas usan su valor por defecto, en silencio. Si se agregan parámetros hay que refrescar la lista o recrear el experimento. Costó un barrido de 400 corridas en el que `turnos` nunca se varió.
18. **Ningún ejemplo de los que trae AnyLogic tiene un experimento Parameter Variation**, así que no hay plantilla XML de la cual copiar el esquema: ese experimento hay que crearlo en el IDE.
19. **Límite de 65.535 bytes de bytecode por método de la JVM.** AnyLogic mete la inicialización de **todas** las variables de un agente en un único método generado (`setupPlainVariables_Main_xjal`). Tres literales de arreglo con 4.240 valores cada uno lo desbordan. Solución: guardar los datos como **String** (una sola instrucción `ldc`) y parsearlos al arranque. El límite de una constante String es 64 KB y el mayor de los tres mide 20 KB.
20. **`<Guard>` existe y es fácil pasarlo por alto.** `Cart.trImmedGotoUnloading` tiene `Trigger="timeout"` con timeout 0 **y** `<Guard>main.truck.atField()</Guard>`. Al auditar una transición hay que leer el `<Guard>` además del trigger, si no se razona sobre lógica que no es la real. Ojo: si la guarda es falsa al expirar el timeout, la transición no dispara y **no se reprograma** — por eso no conviene endurecer guardas sin verificar que exista otro camino de salida del estado (acá lo hay: `trTruckArrived` por mensaje).
21. **Conservar masa no prueba que la fuente sea correcta** (commit `7e66a63`, 2026-08-27). `tankControl` rearmaba `harvestRate()` en los entry/exit del tanque sin mirar `puedeTrabajar()`: la tolva se llenaba de noche y con el lote embarrado. `auditarMasa()` no lo vio, porque `totalCosechado` crecía en paralelo al nivel y la `FUGA` seguía en 1e-11. Arreglo: la tasa pasó a ser **derivada y no latcheada**, con la bandera `Combine.trabajando` y la función `tasaCosechaActual()`, usadas en los tres entry/exit del tanque y en parar/reanudar.
22. **`terminarAlCerrarCampania` tiene que estar en `false` en el experimento `Simulation`.** Con `true` (el default de `Main`), `onCompleted()` llama a `finish()` en el mismo instante en que `siembraCompleta` pasa a `true`: `Creciendo` y `Maduro` son inalcanzables y `gdd` queda en 0. El barrido sí la usa en `true`, a propósito.

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
- **Deuda semántica:** `siembraCompleta` hoy significa "la pasada terminó". Cuando se agregue la campaña de siembra habrá que revisar el nombre y probablemente separar en dos banderas, o mejor, usar `inState()` como única fuente de verdad. Ver 7 bis.

### 7 bis. Estado real de siembra y cosecha (verificado 2026-10-05)

> **Reemplazado el 2026-10-05.** Lo que sigue de esta sección describe el modelo **anterior** (la pasada de octubre era una cosechadora). El estado actual (siembra real, ciclo `SinSembrar → Creciendo → Maduro → Cosechado`, una corrida = una campaña, clima de 365 días) está en [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
>
> Corrida de verificación (campaña 0, 12 lotes, 1 turno): siembra cierra el día 40 (198,9 h = 12 × 16,57; 0 viajes), el cultivo madura el día 168, la cosecha cierra el día 236 (253,1 h = 12 × 21,09; 75 viajes; 16 días sin piso) y `FUGA` = 5e-9. El resumen de cosecha dice 74 viajes porque el viaje 75 termina después del cierre; el grano de ese camión está contado en `enSistema`.

**En el modelo no existe la siembra.** La única máquina es `Combine`, una cosechadora: `harvestRate()` = velocidad × plataforma × `HarvestDensity`, y lo que recorre la cadena es grano cosechado (`totalCosechado`) que termina en el silo.

Lo que sí es de siembra es el **calendario y el nombre de las variables**:
- El reloj arranca el 1/10 y el clima embebido cubre del 1/10 al 30/4.
- `diaFinSiembra` se mide contra el día 45 (15/11), que es una ventana de siembra.
- `Main.onCompleted()` cuenta lotes y, cuando `lotesCompletados == cantidadLotes`, pone `siembraCompleta = true` e imprime `CAMPANIA CERRADA`.

Una corrida del experimento `Simulation` (con `terminarAlCerrarCampania = false`) hace esto:

1. **Pasada 1, desde el 1/10.** La cosechadora recorre todos los lotes. Se interpreta como "la siembra", pero mecánicamente es una cosecha de 3 t/ha.
2. `siembraCompleta = true` → `Creciendo` durante `triangular(90,150,120)` días.
3. `Maduro` → acción de `Maduro → SinSembrar`: resetea contadores, `siembraCompleta = false`, `combine.moveControl.onChange()`.
4. **Pasada 2, a partir de febrero.** La misma cosechadora vuelve a salir. Esta sí es, por calendario, la cosecha real.

Consecuencias:
- **El entregable #1 mide la pasada 1.** El barrido corta ahí (`terminarAlCerrarCampania = true`). Por lo tanto la tabla de la sección 9 bis es la capacidad de **una cosechadora** (4,93 ha/h nominal) con el clima de octubre y noviembre. Una sembradora real tiene otro ancho de labor, otra velocidad y otra logística (semilla y fertilizante que entran, no grano que sale).
- **Bug en la pasada 2:** la acción de `Maduro → SinSembrar` hace `diaCampania = 0`, así que la cosecha de febrero vuelve a leer el clima desde el 1/10. Además el clima termina el 30/4, que corta la cosecha de soja de primera (abril-mayo). No afecta al barrido, pero sí a cualquier medición de la cosecha.
- La transición `SinSembrar → Creciendo` usa la bandera y no `inState()`.

**Decisión abierta (2026-10-05).** El equipo acordó que por ahora el modelo debe ser **solo cosecha**, y la siembra se agrega después. Para que eso sea consistente hay que elegir entre:
- **(A) Mover el calendario a cosecha.** La pasada que se mide es la cosecha: la ventana objetivo pasa a ser de cosecha (fecha de madurez → fecha límite) y el clima tiene que cubrir esos meses. La siembra entra más adelante como la primera pasada, con una máquina parametrizada por modo.
- **(B) Mantener la pasada 1 como proxy de siembra** y declararlo como simplificación en el informe. Es lo más barato, pero contradice "solo cosecha".

Hasta resolverlo, no renombrar variables ni tocar `cicloCultivo`.

**Velocidad de simulación controlada desde el statechart** (API verificada):
- `SinSembrar` entry: `getEngine().setRealTimeScale( 0.5 * day() );` — la máquina siembra (desde 2026-10-05; antes era `0.05 * day()` y la siembra tardaba unos 13 minutos). `Maduro` entry usa `0.05 * day()`. Detalle en [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
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

**Resuelto (verificado 2026-10-05):** `Main` guarda la foto de los contadores al inicio de cada campaña (`baseCosechando`, `baseDetenida`, `baseViajes`, `baseSinPiso`, en la acción de `Maduro → SinSembrar`) y `auditarMasa()` imprime el delta en la línea `CAMPANIA n`.

---

## 9 bis. Clima, jornada laboral y el resultado del entregable #1 (2026-08-11)

### Datos climáticos

Serie diaria **real** embebida en el modelo: **NASA POWER** (reanálisis MERRA-2), punto −33,0 / −61,0 (zona de Rosario), **20 campañas 2005/06 a 2024/25**, 212 días cada una (1/10 al 30/4), **cero valores faltantes**. Se baja con una sola llamada HTTP, sin registro ni API key:

```
https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=ag&longitude=-61.0&latitude=-33.0&start=20051001&end=20250430&format=CSV
```

Validado contra la climatología de Rosario: lluvia anual mediana 1.031 mm, temperatura media 25,8 °C en enero y 10,6 en julio.

Están embebidos **como String y no como literal de arreglo** (ver aprendizaje 19) en `climaLluvia`, `climaTmedia` y `climaEt0`, y los parsea `cargarClima()` desde el StartupCode de Main. Así el `.alp` queda autocontenido y corre igual en las dos máquinas, sin rutas externas que se rompan al cambiar de SO.

**ET0 precalculada con Hargreaves (FAO-56)** a partir de Tmax, Tmin y latitud. Validada: 6,6 mm/día en enero, 1,7 en julio. Va como dato porque es una cantidad física, no una decisión de modelado; el coeficiente de cultivo `kc` sí queda como parámetro.

**Salvedad a declarar en el informe:** es reanálisis satelital, no serie de estación. La celda mide ~50×60 km, así que promedia en el espacio, suaviza los extremos de lluvia y por lo tanto **subestima levemente los días perdidos**. Es de uso estándar en modelado de cultivos.

### El modelo de piso

Balance hídrico **diario** de una capa **superficial**, en el statechart `climaControl` de Main (estado `Dia` con autotransición horaria):

```
humedadSuperficie = clamp( humedadSuperficie + lluvia − kc·ET0, 0, capacidadSuperficie )
daPiso = humedadSuperficie <= umbralPiso && lluvia < lluviaBloqueante
```

Parámetros: `capacidadSuperficie` 35 mm, `umbralPiso` 25 mm, `lluviaBloqueante` 5 mm.

**Un balde de perfil completo (150 mm) NO sirve.** Con ET0 de 5 a 7 mm/día en la ventana el perfil se seca y da **0 días sin piso en casi todas las campañas**: la lluvia nunca detendría la máquina y el entregable quedaría degenerado. El fenómeno real no es el perfil cargado sino la **superficie mojada justo después de la lluvia**. Con la capa superficial: **media 11,2 días no trabajables de 46, mínimo 4, máximo 24**.

El piso por lluvia del día (`lluviaBloqueante`) hace falta porque el balde solo daba 0 días en tres campañas, artefacto del suavizado de MERRA-2.

`umbralPiso` es **el parámetro más influyente del modelo** y no tiene un valor publicado único. Amerita análisis de sensibilidad explícito en el informe.

### La jornada laboral

**Ley 26.727, Régimen de Trabajo Agrario: 8 h diarias y 44 h semanales** (lunes a sábado 13:00). **No** es el régimen general de 48 h — conviene citar el específico.

**Las 8 h son por operario, no por máquina.** Con turnos la máquina trabaja más horas sin violar la jornada, así que las horas-máquina por día son una **variable de decisión** y no un supuesto escondido. Parámetros: `horasSemanales` (44), `turnos` (1-3), `horaInicio` (6). Horas-máquina por día = `horasSemanales × turnos / 7`.

Con 4 turnos se excederían las 24 h del día: **3 turnos es el techo físico de una máquina**.

Simplificación declarada: la jornada semanal se reparte **uniforme sobre los 7 días**, porque en la ventana de siembra se trabaja también fin de semana (tarea estacional). Si se exigiera domingo libre, la capacidad cae ~14%.

La jornada entró como **un término más de `puedeTrabajar()`**, sin mecanismos nuevos. Ese fue el rédito concreto del refactor de la parada por condición única.

### Resultado: P(terminar la siembra antes del 15/11)

300 corridas: `cantidadLotes` 6→30 paso 6 × `turnos` 1→3 × `campania` 0→19.

> **Rehecho el 2026-08-27** (commit `7e66a63`), tras corregir que la tolva se llenaba con la máquina detenida (aprendizaje 21). Es el `resultados.csv` versionado; los números de abajo se recalcularon de ese archivo el 2026-10-05. Respecto de la tabla original, dos celdas bajaron: 624 ha con 1 turno (100% → 95%) y 1.872 ha con 2 turnos (65% → 55%). La tabla original subestimaba el costo logístico.

| Superficie | 1 turno (6,3 h/d) | 2 turnos (12,6 h/d) | 3 turnos (18,9 h/d) |
|---|---|---|---|
| 624 ha | 95% | **100%** | **100%** |
| 1.248 ha | 0% | **100%** | **100%** |
| 1.872 ha | 0% | 55% | **100%** |
| 2.496 ha | 0% | 0% | **90%** |
| 3.120 ha | 0% | 0% | 35% |

Medianas del día de fin, casi exactamente proporcionales a los turnos (las 300 corridas terminaron dentro de los 212 días de datos):

| Superficie | 1 turno | 2 turnos | 3 turnos |
|---|---|---|---|
| 624 ha | 33 | 14,5 | 8 |
| 1.248 ha | 60 | 29,5 | 18,5 |
| 1.872 ha | 87 | 44,5 | 29,5 |
| 2.496 ha | 113,5 | 58,5 | 39 |
| 3.120 ha | 148,5 | 71,5 | 48,5 |

**Capacidad efectiva: ~21 ha/día por turno**, estable desde 1.248 ha (rango 20,8 a 22,5). En 624 ha la cifra se aleja (19 a 26) porque son pocos días y pesa la discretización. Es el **70% de la nominal** (6,29 h × 4,93 ha/h = 31 ha/día); el 30% restante se lo llevan los viajes a la cabecera, las esperas del carro y la jornada que corta las pasadas por la mitad. **Que la capacidad por turno no se degrade al escalar** significa que la logística acompaña y el cuello de botella sigue siendo la máquina — resultado que vale reportar por sí mismo.

### La respuesta de dimensionamiento

> Una máquina cubre **~900 ha por turno de operario** con 90% de confianza de cerrar la ventana. Con los 3 turnos posibles, **una máquina topea en ~2.500 ha**; por encima hace falta una segunda.
>
> Un turno más y una máquina más aportan **la misma capacidad** (~900 ha), pero el turno solo cuesta un salario y la máquina cuesta alquiler más salario. **Conviene sumar turnos hasta agotar los tres y recién después máquinas.** El punto de quiebre está en las 2.500 ha.

**Esta tabla es un límite optimista: todavía no hay roturas de máquina.** Y mide una pasada de **cosechadora** con calendario de siembra (sección 7 bis). Cuando entren, la capacidad efectiva baja y los umbrales se corren hacia abajo.

Celdas de transición sin resolver: 1.872 ha con 2 turnos (55%) y 3.120 ha con 3 turnos (35%). Un barrido de `cantidadLotes` 14→26 paso 2 con `turnos` 2 y 3 los precisa.

### Cómo reproducirlo

Experimento `ParametersVariation`. Model time: **Stop at specified time = 31** (semanas — la unidad del modelo es Week), start date 01/10/2005. Con `terminarAlCerrarCampania = true` el modelo llama a `finish()` al cerrar la siembra, así que **cada corrida es una observación limpia**; si no cierra dentro de los 212 días de datos, `diaFinSiembra` queda en **−1**, que es la observación "no terminó" y no un error.

El experimento `Simulation` tiene `terminarAlCerrarCampania = false`, para que se vea el ciclo completo (aprendizaje 22).

"Before each experiment run" borra `resultados.csv` y escribe el encabezado `lotes;turnos;campania;diaFinSiembra`. La ruta es relativa a la carpeta del modelo y los `catch` hacen `traceln` visible (antes apuntaba a `/home/renaiss/...` y fallaba en silencio en las otras máquinas). Una fila por corrida, desde "After simulation run":

```java
w.println( root.cantidadLotes + ";" + root.turnos + ";" + root.campania + ";" + root.diaFinSiembra );
```

Se escribe a archivo y no con `traceln` porque la consola de AnyLogic recorta el buffer y 300 filas no entran.

---

## 10. Hoja de ruta pendiente

En orden de valor recomendado:

1. ~~Verificar la corrida tras la corrección de overrides~~ — **hecho 2026-08-07**, ver sección 9. Dejó dos pendientes concretos:
   - ~~Cerrar el eslabón carro→camión~~ — **aplicado y verificado 2026-08-07** (tasas apareadas en `Cart.Unloading`, sección 8).
   - ~~Verificar la `FUGA`~~ — **cerrada**: ruido de punto flotante en las dos campañas. **La base de logística ya es confiable**, se puede calibrar y medir sobre ella.
   - ~~Reportar los contadores **por campaña**~~ — **hecho** (sección 9).
0. ~~Definir el alcance cosecha/siembra~~ — **hecho 2026-10-05** (siembra v1 sin semilla). Falta la **v2 con reabastecimiento de semilla**: la sembradora gasta semilla y el carro se la lleva desde la cabecera; el tiempo parado esperando semilla es dato del entregable #2.
0. **Rehacer el barrido** del entregable #1 con el modelo nuevo (`resultados.csv` es del anterior; ahora trae `diaMadurez` y `diaFinCosecha`). Recrear `ParametersVariation` si se quieren barrer `velocidadSiembra`, `velocidadCosecha` o `diaLimiteSiembra`.
2. **Fallas de máquina — máxima prioridad de implementación.** Es lo único que falta para que el #2 y el #3 tengan base completa, y además la tabla de resultados del entregable #1 es un límite optimista sin ellas. Diseño listo, sin implementar. Tercer statechart paralelo en `Combine` (junto a `tankControl` y `moveControl`): `Operativa ──[timeout horasHastaFalla]──> Reparando ──[timeout duracionReparacion]──> Operativa`. El reloj de desgaste se consume **solo mientras la máquina trabaja**, acoplado a `MoveHarvesting` con el mismo patrón que los niveles, y el timeout se expresa `inState( MoveHarvesting ) ? horasHastaFalla : 1e12`. **Detalle de orden importante:** el `STOP` lo manda `Reparando` al entrar, no la transición de falla, para que el rearmado guardado de `MoveHarvesting` se saltee solo y no haya `cancel()` sobre una transición que está disparando.
   - **Distribución:** exponencial con MTBF en **horas de operación** (justificable por superposición de procesos de falla, teorema de Drenick). Weibull con β>1 solo si se declara explícitamente el supuesto de reparación perfecta; para desgaste acumulado real el modelo correcto sería un proceso de Poisson no homogéneo con ley de potencia.
   - **Parámetros:** MTBF del orden de 20-40 h de operación (estudios de cosechadoras reportan MTBF por subsistema de 15 a 72 h; referencia oficial: ASABE D497.7). Reparación asimétrica a derecha, ej. `triangular(0.5, 8, 2)` horas. Costo = fijo + horario.
   - **Criterio de calibración:** apuntar a 0,5–3 fallas esperadas por campaña (`horas_campaña / MTBF`).
   - Los parámetros nuevos obligan a **recrear** `ParametersVariation` (aprendizaje 17).
3. ~~Tabla climática~~ — **hecho 2026-08-11**, y con series históricas reales en vez de sintéticas. Ver sección 9 bis.
4. **Clima — hecho a medias.** El balance hídrico y la compuerta de piso están andando (sección 9 bis). **Queda pendiente el acoplamiento térmico:** `gdd` se acumula en el tick pero **no se usa** en ningún lado; `Creciendo → Maduro` sigue siendo un timeout sobre `diasHastaMadurez = triangular(90,150,120)`. Para cerrarlo, pasar esa transición a condition `gdd >= gddObjetivo` (el `cicloCultivo.onChange()` ya se llama en el tick). El objetivo calibrado contra la serie real es **1.680 grados-día base 10 °C**, que da un ciclo medio de 119,7 días con dispersión de 101 a 135. Dato que importa: el `triangular(90,150,120)` actual abarca 60 días de rango cuando **la variabilidad real es de 34** — la distribución inventada es casi el doble de ancha y sesga el riesgo hacia arriba.
5. **Crecimiento visual — hecho a medias (2026-09-09).** `rectangle3` se reemplazó por la figura 3D replicada `crop3D` (`3d/low_poly_wheat.dae`, escala fija 8) en Main, y `Xunits`/`Yunits` (4.000 plantas) se distribuyen en una grilla proporcional al lote. **Falta que la planta crezca:** ligar su escala o altura a `progresoCultivo()`, calculado desde `tInicioCrecimiento` (ya creada) y `diasHastaMadurez`, o desde `gdd / gddObjetivo` si se hace el ítem 4. **No crear un agente por planta**, sería un desperdicio y consume el cupo de tipos de agente.
6. **Campaña de siembra.** Reusar el patrón de recipientes con el flujo invertido (la semilla sale de la sembradora hacia el lote y los camiones la reponen). Conviene **una sola clase de máquina parametrizada** por modo (siembra/cosecha) en vez de duplicar, por el límite de 10 tipos de agente.
7. **Acople de rinde:** `rindeEfectivo = rindePotencial * penalizacionPorFecha( fechaSiembra )`, con la curva armada como lookup table a partir de datos de INTA de fecha de siembra contra rendimiento. Sin este acople, siembra y cosecha son dos simulaciones pegadas y el modelo no puede responder su propia pregunta.
8. ~~Monte Carlo~~ — **hecho 2026-08-11**. 300 corridas, curva de probabilidad y respuesta de dimensionamiento en la sección 9 bis. **El entregable #1 está cerrado.**
9. Contadores de ocio para carro y camión (solo está hecho el de la cosechadora). **Es la base del entregable #2** (cuellos de botella): sin ellos solo se puede reportar la espera de la cosechadora.
10. **Análisis financiero (entregable #3).** Depende del ítem 7 (acople de rinde) y necesita costos de alquiler, salario por turno, reparación y precios de pizarra (sección 11).
11. **Cierre de resultados.** Barrido fino de las celdas de transición y análisis de sensibilidad a `umbralPiso`, rehechos con fallas. Conviene dejarlo para el final.

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
