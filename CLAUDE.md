# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Un único modelo de **AnyLogic 8.9.9 Personal Learning Edition**: `Optimización de la Ventana de Siembra.alp`. No hay build system, ni tests, ni dependencias: el `.alp` es un XML autocontenido con el código Java embebido dentro de los elementos del modelo.

Trabajo práctico de Simulación (UTN Rosario): dimensionar maquinaria agrícola y logística para cerrar la siembra dentro de la ventana agronómica óptima. Modelo híbrido — eventos discretos (ciclo siembra/recarga) + balance hídrico continuo que frena las máquinas cuando el suelo no "da piso".

**[docs/CONTEXTO-TRASPASO.md](docs/CONTEXTO-TRASPASO.md) es la fuente de verdad del estado del proyecto**: calibración, resultados medidos, hoja de ruta y los aprendizajes técnicos completos. Leerlo antes de tocar el modelo. Este archivo es el resumen operativo.

## Comandos

No hay CLI de build. El flujo real es: editar el `.alp` con scripts, abrir AnyLogic, correr el experimento.

**Inspeccionar el modelo sin abrir AnyLogic** (más rápido y confiable que la GUI para auditar):

```bash
python3 - <<'EOF'
import xml.etree.ElementTree as ET
r = ET.parse("Optimización de la Ventana de Siembra.alp").getroot()
for aoc in r.iter('ActiveObjectClass'):
    n = aoc.findtext('Name')
    if not n: continue                       # los ActiveObjectClass sin Name son refs embebidas
    print(n, [v.findtext('Name') for v in aoc.iter('Variable') if v.get('Class')=='PlainVariable'])
    for e in aoc.iter('StatechartElement'):  # estados y transiciones
        print("  ", e.get('Class'), e.findtext('Name'))
EOF
```

Las acciones/guardas viven en `StatechartElement/Properties/{Action,Guard,Condition,Timeout}`; los parámetros son `<Variable Class="Parameter">`; las funciones, `<Function><Body>`.

**Editar el `.alp` con script** — procedimiento obligatorio:
1. Copia de respaldo fechada (`backups/AAAA-MM-DD-motivo.alp`).
2. Reemplazos que **aborten si el patrón no aparece exactamente una vez**.
3. Validar con `xml.etree.ElementTree.parse`.
4. Verificar además el **nodo padre** en el que se insertó y la indentación — que parsee no alcanza (AnyLogic normaliza y deja diffs ilegibles).

Se puede editar con AnyLogic abierto: detecta el cambio y ofrece recargar. Mirar antes el `.alp.autosave`: si es más nuevo, hay estado en memoria sin volcar.

**Verificar una API de AnyLogic** — con `javap`, nunca de memoria:

```bash
AL=/home/lucaolivieri/Downloads/anylogic          # ver tabla de entornos más abajo
$AL/jre/bin/javap -classpath $AL/plugins/com.anylogic.engine_8.9.9.*/com.anylogic.engine.jar \
  com.anylogic.engine.TransitionTimeout
```

Usar el glob `com.anylogic.engine_8.9.9.*` y no `com.anylogic.engine_*`: en esta máquina conviven el plugin 8.9.8 y el 8.9.9 (la actualización se hizo encima de la instalación vieja), y el glob amplio expande a dos jars y rompe el `-classpath`. Algunas clases (`UtilitiesRandom`) no están en ese jar; para esas, armar el classpath desde el `.classpath` del proyecto del workspace.

**Correr:** en el IDE. Dos experimentos:
- `Simulation` — corrida única, modo *Real time with scale* (el statechart `cicloCultivo` cambia la escala de tiempo por estado: siembra 0,5 días/s, cosecha 0,05 días/s, crecimiento 1 semana/s). El dibujo del campo es **un lote**: la máquina lo repite `cantidadLotes` veces; el avance total se ve en `textAvance` y en la fila de cuadraditos `rectLote` (ver sección 6 bis de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md)).
- `ParametersVariation` — Monte Carlo. Varía `campania` 0→19, `cantidadLotes` 6→30 paso 6, `turnos` 1→3. Stop at specified time = **31** (la unidad del modelo es **Week**), start date 01/10/2005. *Before each experiment run* borra `resultados.csv` y escribe el encabezado (`lotes;turnos;campania;diaFinSiembra`); *After simulation run* appendea una fila. La ruta es relativa (`"resultados.csv"`) y los `catch` hacen `traceln` visible. El `resultados.csv` versionado es el barrido de 300 corridas vigente.

⚠️ Si se agregan parámetros a `Main` (por ejemplo los de fallas), hay que **recrear** `ParametersVariation`: su lista de parámetros quedó congelada al crearlo.

## Entornos

El proyecto se comparte entre tres máquinas. **Verificar en cuál estás antes de razonar sobre rutas** — las rutas absolutas de los docs y del `.alp` son de otros entornos, no del tuyo.

| | Esta máquina (Luca) | Otro integrante (Ubuntu) | Santiago (Windows) |
|---|---|---|---|
| AnyLogic | `/home/lucaolivieri/Downloads/anylogic` (8.9.9) | `/home/renaiss/Descargas/anylogic` (8.9.9) | `C:\Program Files\AnyLogic 8.9 Personal Learning Edition\` (8.9.9) |
| Modelo | `~/Desktop/facultad/simulacion/harvest-model` (este repo) | `/home/renaiss/Models/Harvest Simulator/` | `C:\Users\Santiago\Models\Optimización de la Ventana de Siembra\` |

`~/Models` en esta máquina tiene otros modelos de la cursada, **no** este.

Las tres máquinas tienen 8.9.9 PLE (verificado en esta el 2026-10-05: `.eclipseproduct` dice `version=8.9.9.202607020720`). Queda el plugin 8.9.8 residual en `plugins/`, ver el `javap` de arriba.

En Ubuntu, AnyLogic (SWT) sobre GNOME/Wayland **no permite arrastrar bloques de la paleta al canvas** y pierde caracteres al tipear (culpa de `ibus-daemon`). Solución verificada: sesión **Xfce**, o lanzar con `GTK_IM_MODULE=xim`.

## Arquitectura

**4 agentes** (`Main`, `Combine`, `Cart`, `Truck`) — de los 10 que permite PLE. Cadena de masa: campo → cosechadora → carro → camión → silo.

### La Fluid Library fue eliminada — y no puede volver

PLE topea el tiempo simulado en **5 horas para toda librería salvo Process Modeling**. El modelo necesita campañas de meses. Se borraron los 12 bloques Fluid **y** el `<RequiredLibraryReference>` (borrar los bloques no levanta el tope).

Cada recipiente es hoy `nivel` / `tasaActual` / `tUltimo` + `actualizarNivel()`, con integración analítica por evento:

```java
double dt = time() - tUltimo;
double bruto = nivel + tasaActual * dt;
if ( bruto > Capacity ) { main.masaDescartada += bruto - Capacity; bruto = Capacity; }
if ( bruto < 0 )        { main.masaInventada  += -bruto;           bruto = 0; }
nivel = bruto; tUltimo = time();
```

- **Tasas** en unidades de tiempo del modelo: `UnloadingRate / second()`.
- **Eventos lleno/vacío** son transiciones **timeout** con unidad SECOND: `( ( Capacity - nivel ) / tasaActual ) / second()`, y `1e12` para desactivar (`infinity()` no existe). Son cinco: `Cart.Full`, `Cart.trBecameEmpty`, `Combine.Full`, `Truck.transition5`, `Truck.transition3`.
- **Regla de acople:** la Fluid acoplaba por puertos con independencia del statechart. Ahora **todo acople es un mensaje explícito**, y el estado que abre un flujo fija **las dos** tasas (emisor y receptor), al entrar y al salir. Ver `Cart.Unloading` y `Combine.WithCart`. Latchear una sola punta fabrica o destruye masa.

### Conservación de masa

`Main.auditarMasa()` (llamada desde `onCompleted()` al cerrar campaña) verifica
`totalCosechado == combine.nivel + cart.nivel + truck.nivel + nivelSilo + masaDescartada − masaInventada`.
Hoy la `FUGA` está en ~1e-10 (ruido de punto flotante): **la cadena conserva**.

Heurística que funcionó tres veces: si la `FUGA` no es ruido, su magnitud es un **múltiplo exacto de la capacidad de un recipiente** e identifica el eslabón roto. Capacidades: 9.000 cosechadora / 20.000 carro / 50.000 camión. Ojo: `masaDescartada`/`masaInventada` **detectan** el desbalance pero **no lo localizan** — solo saltan en los clamps.

### Clima y jornada

`Main.climaControl` (estado `Dia`, autotransición horaria `tickDiario`) corre un balance hídrico **de capa superficial** (no de perfil: un balde de 150 mm da 0 días sin piso y degenera el entregable):

```
humedadSuperficie = clamp( humedadSuperficie + lluvia − kc·ET0, 0, capacidadSuperficie )
daPiso = humedadSuperficie <= umbralPiso && lluvia < lluviaBloqueante
```

Series **reales de NASA POWER** (20 campañas 2005/06–2024/25, 212 días c/u) embebidas **como String** en `climaLluvia`/`climaTmedia`/`climaEt0` y parseadas por `cargarClima()` desde el StartupCode — literales de arreglo desbordan el límite de 65.535 bytes de bytecode por método de la JVM.

`Main.dentroDeJornada()` modela la Ley 26.727 (44 h semanales **por operario**), repartida uniforme sobre 7 días; `turnos` (1–3) es variable de decisión.

**Punto único de parada:** `Combine.puedeTrabajar()` = `main.daPiso && main.dentroDeJornada() && !inState(FullWaitCart)`. Todo motivo nuevo de parada (roturas, etc.) va **ahí**, no como mensaje nuevo.

### Ciclo de cultivo, siembra y cosecha

`Main.cicloCultivo` (desde 2026-10-05): `● ──> SinSembrar ──[siembraCompleta]──> Creciendo ──[timeout diasHastaMadurez]──> Maduro ──[cosechaCompleta]──> Cosechado`.

**Una corrida = una campaña** (la serie de clima cubre 1/10 a 30/9, día 0 = 1/10). `Cosechado` es estado final: para otra campaña se cambia el parámetro `campania` (0–19), no se reinicia el ciclo.

**Una sola máquina (`Combine`) con dos modos**, deducidos del estado del campo: `Main.sembrando()` = `inState( SinSembrar )`. Sembrando, `Combine.tasaCosechaActual()` da 0 (no entra grano, carro y camión quedan quietos) y la velocidad es `velocidadSiembra` (7 km/h); cosechando, `velocidadCosecha` (5,5 km/h). Sale del galpón con `Main.laborPendiente()` (hay campo por sembrar o maduro, y quedan lotes).

`Main.onCompleted()` lo llama `Combine` por cada lote; al cerrar todos los lotes de la pasada fija `diaFinSiembra` (contra `diaLimiteSiembra` = 45, 15/11) o `diaFinCosecha`/`diaMadurez`, e imprime `reportarPasada()`.

`gdd` se acumula en el tick pero **todavía no se usa**: la maduración sigue siendo `triangular(90,150,120)`. El objetivo calibrado es `gddObjetivo = 1680`.

Explicación completa y decisiones: [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md). Verificado con `Simulation` (12 lotes, 1 turno, campaña 0): siembra cierra el día 40 (198,9 h, 0 viajes), maduro día 168, cosecha cierra el día 236 (253,1 h, 75 viajes), `FUGA` = 5e-9.

**Clima:** `herramientas/clima_nasa.py` baja NASA POWER a `datos/` y reescribe las tres series String del `.alp` (365/366 días por campaña). `--verificar` solo compara.

## Trampas verificadas (cada una costó una corrida fallida)

Las 22 completas están en la sección 5 de [docs/CONTEXTO-TRASPASO.md](docs/CONTEXTO-TRASPASO.md). Las que más muerden:

- **`Transition.restart()` no existe** en 8.9.9. La API es `start()` / `cancel()`; `start()` reevalúa el timeout.
- **Las transiciones de salida se activan DESPUÉS del entry action.** Si el entry fija la tasa, el timeout ya la ve → no reprogramar. Llamar `cancel()` en el entry del propio estado origen tira `RuntimeException: a statechart transition being deactivated is not active`. **Nunca reprogramar en un exit action.**
- **`return` prohibido en acciones de transición y de estado.** AnyLogic las despacha desde un método compartido (`executeActionOf`): el `return` sale del despachador y saltea el rearmado de la autotransición. Envolver en `if`. Dentro de una `Function` el `return` es normal.
- **Las condiciones no se re-evalúan cuando la variable la cambia otro agente.** Toda condición que dependa de una variable ajena necesita un `Statechart.onChange()` explícito desde donde se modifica (`combine.moveControl.onChange()`, `cicloCultivo.onChange()`).
- **`SelectionModeForSimultaneousEvents` está en LIFO** y rompe handshakes de dos mensajes del mismo instante; una transición por mensaje **no encola**, si el estado no está activo el mensaje se descarta en silencio. **No cambiar a FIFO como arreglo** — sirve para confirmar el diagnóstico, tapa el bug real.
- **Los objetos embebidos pisan los parámetros del tipo de agente.** Cambiar el default de `Truck` no hace nada si la instancia `truck` en `Main` tiene override. Revisar siempre los overrides de instancia antes de diagnosticar.
- **El `.alp` serializa los campos de todos los tipos de trigger**, no solo el activo: al auditar mensajes, filtrar por `Trigger="message"`. Y leer el `<Guard>` además del trigger (ej. `Cart.trImmedGotoUnloading`) — si la guarda es falsa al expirar el timeout, la transición **no se reprograma**.
- **La lista de parámetros de un Parameter Variation se congela al crearlo.** Los parámetros agregados a `Main` después no aparecen y corren con su default, en silencio. Costó un barrido de 400 corridas.
- **Límites PLE:** 10 tipos de agente, 200 bloques por tipo, 50.000 agentes dinámicos.

## Convenciones

- El modelo, los comentarios y los `traceln` están **en español sin tildes** (el código embebido en el `.alp`). Los docs sí llevan tildes.
- Commits en español, formato `tipo: descripción` (`feat:`, `fix:`, `docs:`).
- Preferencia del autor: aplicar los cambios mecánicos directamente sobre el `.alp`; guiar en el IDE cuando hay que dibujar elementos nuevos de statechart. Pide análisis previo cuando hay una decisión de modelado de por medio.

## Estado y próximo paso

Entregable #1 con la **tabla vieja** (sección 9 bis del contexto): medía una pasada de cosechadora en octubre y hay que **rehacerlo** con el modelo nuevo (siembra real + clima anual). Hecho después: contadores por pasada (`reportarPasada()`), CSV con ruta relativa, cultivo 3D en grilla (`crop3D`, todavía sin crecer), clima anual y siembra v1 (sin semilla).

**Lo que falta, en orden:** siembra v2 con reabastecimiento de semilla (el carro lleva semilla a la sembradora; la espera es dato del entregable #2), rehacer el barrido (`ParametersVariation` hay que **recrearlo** si se quieren barrer parámetros nuevos), fallas de máquina (diseño listo en la sección 10 del contexto), `gdd → Maduro`, contadores de espera de carro y camión, acople de rinde y costos, sensibilidad a `umbralPiso`.
