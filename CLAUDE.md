# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Un único modelo de **AnyLogic 8.9.9 Personal Learning Edition**: `Optimización de la Ventana de Siembra.alp`. No hay build system, ni tests, ni dependencias: el `.alp` es un XML autocontenido con el código Java embebido dentro de los elementos del modelo.

Trabajo práctico de Simulación (UTN Rosario): dimensionar maquinaria agrícola y logística para cerrar la siembra dentro de la ventana agronómica óptima. Modelo híbrido — eventos discretos (ciclo siembra/recarga) + balance hídrico continuo que frena las máquinas cuando el suelo no "da piso".

**[docs/CONTEXTO-TRASPASO.md](docs/CONTEXTO-TRASPASO.md) es la fuente de verdad del estado del proyecto**: calibración, resultados medidos, hoja de ruta y los aprendizajes técnicos completos. Leerlo antes de tocar el modelo. Este archivo es el resumen operativo.

**[docs/PLAN.md](docs/PLAN.md) es el plan de trabajo vigente** (pasos, decisiones, criterios de aceptación y estado de cada uno). [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md) explica el modelo de siembra, cosecha y clima anual.

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
- `Simulation` — corrida única, termina al cerrar la cosecha (`terminarAlCerrarCampaña = true`), modo *Real time with scale* (el statechart `cicloCultivo` cambia la escala de tiempo por estado: siembra 0,5 días/s, cosecha 0,05 días/s, crecimiento 1 semana/s). El dibujo del campo es **un lote**: la máquina lo repite `cantidadLotes` veces; el avance total se ve en `textAvance` y en la fila de cuadraditos `rectLote` (ver sección 6 bis de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md)).
- `ParametersVariation` — Monte Carlo del sistema base (12 lotes, 1 tren) contra el alternativo C (18 lotes, 2 trenes de 9), parte 4.5 de [docs/PLAN.md](docs/PLAN.md). Varía `campaña` 0→19, `cantidadLotes` 9 y 12, `replica` 1→5 y `tren` 1→2, con `turnos` fijo en 1 (400 corridas). Las semillas se derivan de `replica` y `tren` (`semillaFallasUsada()`, `semillaMadurezUsada()`). Stop at specified time = **52** (la unidad del modelo es **Week**; antes 31), start date 01/10/2005. *Before each experiment run* borra `resultados.csv` y escribe el encabezado; *After simulation run* appendea una fila. Son 59 columnas en UTF-8 (con `replica`, `tren`, las semillas usadas y `gddMeta`): parámetros y días de fin, 23 contadores por pasada (`s_` siembra, `c_` cosecha, de `Main.filaPasada()`) y los días de cada lote separados por `|` (sección 15 de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md)). La ruta es relativa (`"resultados.csv"`) y los `catch` hacen `traceln` visible. ⚠️ El `resultados.csv` versionado es del **modelo anterior** (4 columnas, pasada de cosechadora en octubre): hay que rehacerlo, ver [docs/PLAN.md](docs/PLAN.md).

⚠️ Si se agregan parámetros a `Main` (por ejemplo los de fallas), hay que **recrear** `ParametersVariation`: su lista de parámetros quedó congelada al crearlo.

## Entornos

El proyecto se comparte entre tres máquinas. **Verificar en cuál estás antes de razonar sobre rutas** — las rutas absolutas de los docs y del `.alp` son de otros entornos, no del tuyo.

| | Esta máquina (Luca) | Otro integrante (Ubuntu) | Santiago (Windows) |
|---|---|---|---|
| AnyLogic | `/home/lucaolivieri/Downloads/anylogic` (8.9.9) | `/home/renaiss/Descargas/anylogic` (8.9.9) | `C:\Program Files\AnyLogic 8.9 Personal Learning Edition\` (**8.9.10** desde el 2026-10-28) |
| Modelo | `~/Desktop/facultad/simulacion/harvest-model` (este repo) | `/home/renaiss/Models/Harvest Simulator/` | `C:\Users\Santiago\Models\Optimización de la Ventana de Siembra\` |

`~/Models` en esta máquina tiene otros modelos de la cursada, **no** este.

⚠️ Santiago pasó a **8.9.10** el 2026-10-28: el `.alp` queda guardado con `AlpVersion="8.9.10"`, y con la misma semilla la cosecha de la corrida C dio una falla más (sección 15 de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md)). El barrido se corre todo con una sola versión. Las otras dos máquinas tienen 8.9.9 PLE (verificado en esta el 2026-10-05: `.eclipseproduct` dice `version=8.9.9.202607020720`). Queda el plugin 8.9.8 residual en `plugins/`, ver el `javap` de arriba.

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

Series **reales de NASA POWER** (20 campañas 2005/06–2024/25, 365 o 366 días c/u, del 1/10 al 30/9) embebidas **como String** en `climaLluvia`/`climaTmedia`/`climaEt0` y parseadas por `cargarClima()` desde el StartupCode — literales de arreglo desbordan el límite de 65.535 bytes de bytecode por método de la JVM.

`Main.dentroDeJornada()` modela la Ley 26.727 (44 h semanales **por operario**), repartida uniforme sobre 7 días; `turnos` (1–3) es variable de decisión.

**Punto único de parada:** `Combine.puedeTrabajar()` = `main.daPiso && main.dentroDeJornada() && !inState(FullWaitCart) && !sinSemilla`. Todo motivo nuevo de parada (roturas, etc.) va **ahí**, no como mensaje nuevo.

### Ciclo de cultivo, siembra y cosecha

`Main.cicloCultivo` (desde 2026-10-05): `● ──> SinSembrar ──[siembraCompleta]──> Creciendo ──[timeout diasHastaMadurez]──> Maduro ──[cosechaCompleta]──> Cosechado`.

**Una corrida = una campaña** (la serie de clima cubre 1/10 a 30/9, día 0 = 1/10). `Cosechado` es estado final: para otra campaña se cambia el parámetro `campaña` (0–19), no se reinicia el ciclo.

**Una sola máquina (`Combine`) con dos modos**, deducidos del estado del campo: `Main.sembrando()` = `inState( SinSembrar )`. Sembrando, `Combine.tasaCosechaActual()` da 0 (no entra grano, carro y camión quedan quietos) y la velocidad es `velocidadSiembra` (7 km/h); cosechando, `velocidadCosecha` (5,5 km/h). Sale del galpón con `Main.laborPendiente()` (hay campo por sembrar o maduro, y quedan lotes).

`Main.onCompleted()` lo llama `Combine` por cada lote; al cerrar todos los lotes de la pasada fija `diaFinSiembra` (contra `diaLimiteSiembra` = 45, 15/11) o `diaFinCosecha`/`diaMadurez`, e imprime `reportarPasada()`.

**Madurez por grados-día (paso 3, verificado 2026-10-27):** `Creciendo` pone `gdd = 0`; el tick suma `max(0, tmedia − tBase)` y `Creciendo → Maduro` es la condición `gdd >= gddMeta`. **Desde el 2026-10-28 la meta tiene distribución:** `gddMeta = triangular(gddMinimo 1.700, gddMaximo 2.100, moda gddObjetivo 1.900)`, sorteada al entrar a `Creciendo` con su propia semilla (`semillaMadurez`, mezclada: `java.util.Random` da casi el mismo primer número con semillas consecutivas). Sección 16 de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md). `diasHastaMadurez` ahora es salida (largo del ciclo); `diasMaduracionMin/Max/Moda` quedan sin uso hasta el paso 9. Medido con `campaña = 0`, sin fallas: 1 lote madura el día 147, 12 lotes el día 177 (cosecha cierra el 243, 74 viajes, `FUGA` 5,9e-9). Sección 13 de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md).

Explicación completa y decisiones: [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md). Verificado con `Simulation` (12 lotes, 1 turno, campaña 0) **antes del paso 3**: siembra cierra el día 40 (198,9 h, 0 viajes), maduro día 168, cosecha cierra el día 236 (253,1 h, 75 viajes), `FUGA` = 5e-9.

**Semilla (paso 1a, 2026-10-19):** tolva `Combine.semilla` integrada como el grano (`tasaSemilla`, `tUltimoSemilla`, `actualizarSemilla()`), con tasa derivada `tasaSemillaActual()` (solo trabajando y sembrando). Llamar a `actualizarTasaSemilla()` donde cambie `trabajando`. Statechart paralelo `Combine.semillaControl`: `Suficiente → Pedida → Agotada`; las vueltas exigen `semilla > umbral + 1 kg` (histéresis, aprendizaje 23). `Cart` tiene `CargandoSemilla → LlevandoSemilla → VolviendoSemilla`, vuelca de golpe y llama a `Combine.semillaEntregada()`; la semilla del carro es `semillaCarro`, nunca `nivel`. `Main.auditarSemilla()` verifica conservación y superficie (145 hileras = 104,4 ha por lote). Stock de la cabecera infinito (decisión: no se modela el stock finito). Detalle: sección 11 de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md).

**Fallas (paso 2, verificado con 1 lote el 2026-10-19 y con 12 lotes el 2026-10-27):** statechart paralelo `Combine.fallaControl`: `Operativa → Reparando → Operativa`. `aFalla` es un timeout en horas, `trabajando ? tHastaFallaHoras() : 1e12`, y `reprogramarFalla()` lo rearma donde cambia `trabajando` (vuelve a sortear al reanudar: la exponencial no tiene memoria). La falla es un motivo más de `puedeTrabajar()` (`!reparando`). Usa su propio `java.util.Random` (`Main.semillaFallas`, mezclada con `* 0x9E3779B97F4A7C15L` desde el 2026-10-28: sin mezcla, las semillas 1, 2 y 3 daban el mismo primer sorteo) para no mover los demás sorteos. Parámetros `mtbfHoras` (100 h, sin fuente) y `semillaFallas`. Detalle y corridas de verificación: sección 12 de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md).

**Causas de parada (paso 4, verificado 2026-10-27):** `Combine.causaActual()` imputa cada hora detenida a una causa con prioridad falla > sinSemilla > jornada > sinPiso > esperaCarro (más `traslado` al lote y `otra`, que tiene que dar 0). `registrarCausa()` cierra el tramo: llamarla donde pueda cambiar una causa (ya está en parar, reanudar, inicio y fin de lote, fin de reparación, salida de `Agotada` y el tick horario). Acumula en `Main.horasParada[]`. `Cart` y `Truck` miden horas por grupo de estados con `cerrarEstado()` en cada entry action; un estado nuevo tiene que llamarla y fijar `estado`. Detalle: sección 14 de [docs/CAMBIOS-2026-10.md](docs/CAMBIOS-2026-10.md).

**Clima:** `herramientas/clima_nasa.py` baja NASA POWER a `datos/` y reescribe las tres series String del `.alp` (365/366 días por campaña). `--verificar` solo compara.

## Trampas verificadas (cada una costó una corrida fallida)

Las 23 completas están en la sección 5 de [docs/CONTEXTO-TRASPASO.md](docs/CONTEXTO-TRASPASO.md). Las que más muerden:

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

- El modelo, los comentarios y los `traceln` están **en español sin tildes** (el código embebido en el `.alp`), **pero con ñ**: `campaña`, `diaCampaña`, `tamaño`, nunca `campania` ni `tamano` (decidido el 2026-10-28; Java y AnyLogic aceptan la ñ en identificadores). Los docs sí llevan tildes.
- Commits en español, formato `tipo: descripción` (`feat:`, `fix:`, `docs:`).
- Preferencia del autor: aplicar los cambios mecánicos directamente sobre el `.alp`; guiar en el IDE cuando hay que dibujar elementos nuevos de statechart. Pide análisis previo cuando hay una decisión de modelado de por medio.

## Estado y próximo paso

Entregable #1 con la **tabla vieja** (sección 9 bis del contexto): medía una pasada de cosechadora en octubre y hay que **rehacerlo** con el modelo nuevo (siembra real + clima anual). Hecho después: contadores por pasada (`reportarPasada()`), CSV con ruta relativa, cultivo 3D en grilla (`crop3D`, crece con `progresoCultivo()` = `gdd / gddObjetivo`), animación de lluvia y piso (color del campo, indicador, gotas 2D y 3D), clima anual, siembra v1 y semilla 1a (carro con stock infinito; verificada en la siembra y en la cosecha con 1 lote). `Simulation` termina al cerrar la cosecha y corre con 512 MB.

**Lo que falta, en orden** (estado al día en [docs/PLAN.md](docs/PLAN.md)): rinde y costos (paso 5), rehacer el barrido (paso 7; el IDE ya agregó los parámetros nuevos a `ParametersVariation`), sensibilidad (paso 8).
