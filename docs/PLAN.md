# Plan de trabajo

Estado al 2026-10-28 (última actualización: paso 7, diseño). Este documento es el plan vigente del proyecto: qué falta, en qué orden, cómo se decide cada cosa y cómo se comprueba que quedó bien. Cada paso tiene un criterio de aceptación que se verifica con una corrida, y un estado que se actualiza al terminarlo.

Para entender el modelo actual, leer primero [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md). Para la historia completa y los aprendizajes de AnyLogic, [CONTEXTO-TRASPASO.md](CONTEXTO-TRASPASO.md).

---

## 1. Qué tiene que poder mostrar el trabajo

La cursada tiene una sola presentación del trabajo completo. Estos son los tres resultados que esa presentación tiene que sostener (sección 1 del contexto):

| # | Resultado | Estado |
|---|---|---|
| 1 | Probabilidad de terminar la siembra antes del 15/11, según la superficie y los turnos, con clima histórico real | **A rehacer.** La tabla vieja medía una pasada de cosechadora. El modelo nuevo siembra de verdad, pero falta el barrido |
| 2 | Cuellos de botella logísticos: tiempo de máquina parada, y por qué | **Parcial.** Solo se mide el tiempo parado de la máquina, sin separar las causas, y no se mide el carro ni el camión |
| 3 | Análisis financiero: costo de máquinas y turnos extra contra el beneficio de no perder rinde | **Sin empezar.** Falta el rinde según la fecha de siembra, los costos y los precios |

---

## 2. Cómo se trabaja cada paso

Todos los pasos siguen el mismo protocolo, para que cualquiera del grupo pueda repetirlo y para no perder cambios.

1. **Rama.** Una rama por paso (`feat/<paso>`), que sale de `main` actualizado.
2. **Respaldo.** Copia fechada del `.alp` en `backups/AAAA-MM-DD-motivo.alp` antes de tocarlo.
3. **Cambio por script.** Cada reemplazo aborta si el patrón no aparece exactamente una vez. Los elementos de statechart nuevos también se pueden agregar por script, como se hizo con `Cosechado`.
4. **Validación.** El XML tiene que parsear, los elementos nuevos tienen que estar en el nodo padre correcto y los `Id` no pueden repetirse.
5. **Corrida en el IDE.** La hace Luca con `Simulation` y pega la consola. Ningún paso se da por terminado sin una corrida.
6. **Criterio de aceptación.** Cada paso tiene valores esperados calculados de antemano. Se compara lo medido contra lo esperado.
7. **Docs y commit.** Se actualiza `CAMBIOS-2026-10.md` (o un documento nuevo) con el qué, el cómo y el porqué, y se hace el commit. El PR lo mergea el grupo.

**Antes de abrir el `.alp` en AnyLogic:** cerrar el modelo sin guardar y reabrirlo. Si el IDE tiene una versión vieja en memoria y se guarda, se pisan los cambios hechos por script.

---

## 3. Mapa de pasos

| Paso | Qué | Resultado | Depende de | Estado |
|---|---|---|---|---|
| 0 | Actualizar docs y armar este plan | Todos | Ninguna | **Hecho** |
| 1 | Siembra con reabastecimiento de semilla | #2 | Ninguna | **Hecho** (1a verificado). El 1b se descartó |
| 2 | Fallas de máquina | #1, #2, #3 | Ninguna | **Hecho** (verificado con 1 y 12 lotes) |
| 3 | Madurez por grados-día (`gdd`) | #1 | Ninguna | **Hecho** (verificado con 1 y 12 lotes) |
| 4 | Causas de parada y contadores de carro y camión | #2 | 1, 2 | **Hecho** (verificado con 12 lotes) |
| 5 | Rinde según la fecha de siembra y costos | #3 | 1, 3, 4 | **Salidas del modelo verificadas**. El cálculo de rinde y costos va en el paso 7 |
| 6 | Crecimiento visual del cultivo | Ninguno | 3 | **Hecho** (tamaño el 27/10; color del campo según el cultivo el 28/10, verificado en el IDE) |
| 7 | Barrido final de Monte Carlo | #1, #2, #3 | 1 a 5 | **En curso**: diseño decidido (parte 4.5) y modelo preparado, sin verificar; falta el script de análisis |
| 8 | Sensibilidad de los parámetros inciertos | #1, #3 | 7 | Pendiente |
| 9 | Informe, regenerar el HTML y limpiar el repo | Ninguno | Todos | Pendiente |

**Orden recomendado:** 1, 2, 3, 4, 5, 7, 8, 9. El paso 6 se hace si sobra tiempo. Los pasos 2 y 3 son independientes del 1 y se pueden intercambiar.

**Por qué este orden.** Los pasos 1 a 3 cambian los tiempos de la simulación. Por eso el barrido (paso 7) va después de todos. El paso 4 necesita que existan las causas de parada (semilla y fallas) para poder medirlas. El paso 5 necesita el día de siembra de cada lote (paso 1) y la madurez realista (paso 3).

---

## 4. Decisiones que cambian el alcance

Estas decisiones las tiene que conocer todo el grupo, porque son las que hay que defender frente al docente.

### 4.1 El modelo no puede simular dos máquinas (**a discutir con el grupo**)

El modelo tiene una sola máquina con su carro y su camión. La pregunta del trabajo ("cuánta maquinaria alquilar") y el resultado #3 ("costo de maquinaria extra") necesitan comparar una máquina contra dos o tres.

**Propuesta:** tratar N máquinas como N trenes independientes (máquina, carro y camión), cada uno con `superficie / N`. Con el mismo clima para todos, la campaña termina cuando termina el tren más cargado. Eso equivale a simular `ceil(lotes / N)` lotes con una máquina. No hace falta código nuevo en el modelo: el análisis del barrido (paso 7) hace la cuenta y el costo se multiplica por N.

**Qué se pierde:** los trenes no comparten recursos (por ejemplo, un camión que atiende a dos máquinas). Se declara como simplificación. Redondear hacia arriba los lotes por tren es conservador.

**Detalle agregado el 2026-10-27, por las fallas.** Cada máquina se rompe en momentos distintos, así que los N trenes ya no son idénticos. Para N máquinas hay que hacer N corridas de `ceil(lotes / N)` lotes con distinta `semillaFallas`, y tomar el día de fin **más tardío**. La cuenta se hace en el script de análisis del paso 7.

**Alternativa: varias máquinas dentro del modelo.** Convertir `combine`, `cart` y `truck` en poblaciones de tamaño N. Las poblaciones no gastan cupo de tipos de agente de PLE. Pero hay que reescribir las ~87 referencias directas a `combine`, `cart` y `truck`, el reparto de lotes (hoy es un solo contador en `onCompleted()`), el cierre de cada pasada, las auditorías de masa y de semilla, y el dibujo del campo. Toca el acople por mensajes entre la máquina y el carro, que es la parte más frágil del modelo, y obliga a verificar todo de nuevo. Solo conviene si se quiere estudiar logística compartida, por ejemplo un carro para dos sembradoras.

**Para decidir en el grupo.** ¿La pregunta del trabajo es "cuántas máquinas alquilar para terminar a tiempo"? Entonces alcanza la propuesta, sin cambios en el modelo. ¿Es "alcanza un carro o un camión para varias máquinas"? Entonces hace falta la alternativa, con su costo en tiempo. Recomendación: la propuesta, declarada como simplificación en el informe. Hay que decidirlo antes del paso 7, porque cambia el diseño del barrido.

### 4.2 Con valores realistas, la semilla casi no frena a la máquina

Una sembradora gasta unos 441 kg de semilla por hora (6,3 ha/h × 70 kg/ha). Con una tolva de 4.000 kg, eso son unas 9 horas de autonomía. Si el carro llega antes de que se vacíe, la máquina nunca espera.

Entonces el desabastecimiento solo aparecería si la reposición fuera lenta. Se decidió el 2026-10-19 **no modelar el stock del depósito**: la cabecera es infinita y el carro siempre encuentra semilla. El resultado para el informe es que, con estos valores, la semilla no es un cuello de botella, y la tolva y el carro de 20 t cubren días de siembra. Se declara como supuesto, junto con `densidadSiembra` y `capacidadSemilla`.

### 4.3 Valores que hay que respaldar con una fuente

Ninguno de estos valores se puede inventar. Cada uno queda marcado en el modelo y en el informe como supuesto hasta tener la fuente:

| Valor | Hoy | Fuente a conseguir |
|---|---|---|
| Velocidad de siembra | 7 km/h | Ficha técnica de sembradora o ASABE D497.7 |
| Densidad de siembra | 70 kg/ha | INTA, recomendación para soja |
| Capacidad de la tolva de semilla | 4.000 kg | Ficha técnica de sembradora |
| MTBF y reparación | A definir | ASABE D497.7 u otro estudio de confiabilidad |
| Meta de grados-día | Triangular (1.700; moda 1.900; 2.100), sorteada por corrida desde el 2026-10-28 | INTA o Bolsa de Cereales: fecha típica de cosecha de soja |
| Pérdida de rinde por siembra tardía | A definir | INTA, ensayos de fecha de siembra |
| Costos y precios | A definir | Ver paso 5 |

### 4.4 Escenarios a comparar (**decidido el 2026-10-28: base contra un sistema alternativo, ver 4.5**)

La consigna pide comparar alternativas y elegir la mejor. Para eso hay que separar dos tipos de factores:

- **Variables de decisión:** lo que el productor elige. Con ellas se arman los escenarios que se comparan.
- **Factores inciertos:** lo que nadie controla. No se eligen. Se repiten para medir el riesgo de cada escenario, o se varían en la sensibilidad (paso 8).

**Variables de decisión.**

| Factor | Cómo está hoy | Qué decisión representa |
|---|---|---|
| Turnos (`turnos`) | Parámetro de 1 a 3, ya se barre | Contratar más operarios |
| Cantidad de máquinas | Se calcula en el análisis (parte 4.1) | Alquilar más equipos |
| Velocidad (`velocidadSiembra`, `velocidadCosecha`) | Parámetros de `Main` | Una máquina más grande o más rápida |
| Equipo nuevo o usado (`mtbfHoras`) | Parámetro de `Main` | Pagar más por un equipo que se rompe menos |
| Tolva de semilla (`capacidadSemilla`, `umbralSemilla`) | Parámetros de `Main` | Tamaño de la sembradora y cuándo pedir semilla |
| Logística de apoyo: capacidad y velocidad del carro, capacidad del camión | Parámetros de `Cart` y `Truck` (20 t, 15 km/h, 50 t) | La consigna la pide explícitamente: "camiones tolva, acoplados tanque" |

La superficie (`cantidadLotes`) es el tamaño del problema, no una decisión. Se presenta como filas de la tabla de resultados: "para 1.250 ha, la mejor opción es...".

**Límite técnico.** `ParametersVariation` solo varía parámetros de `Main`. Para barrer el carro y el camión hay que subir sus parámetros a `Main` y pasarlos a las instancias `cart` y `truck`, que hoy tienen valores fijos (`truck.Capacity = 50000` y `cart.Speed = 15`). Es un cambio mecánico, por script.

**Factores inciertos.**

| Factor | Cómo se usa |
|---|---|
| Clima (`campaña`, 0 a 19) | Cada escenario se corre con los 20 años. De ahí sale la probabilidad de terminar a tiempo |
| Fallas (`semillaFallas`) | Varias réplicas por escenario |
| Madurez (`semillaMadurez`) | Meta de grados-día triangular, sorteada por corrida. Varias réplicas por escenario, con las mismas semillas en todos |
| Suelo (`umbralPiso`, `lluviaBloqueante`, `capacidadSuperficie`) | Sensibilidad. Se puede presentar como "suelo pesado o liviano" |
| Cultivo (`gddObjetivo`, `densidadSiembra`, `diaLimiteSiembra`) | Sensibilidad. `gddObjetivo` también podría ser una decisión (variedad de ciclo más corto), pero cambia el rinde y no hay datos para modelarlo |
| Precios y costos (paso 5) | Sensibilidad del margen |

**Criterios para comparar.** Salen de la consigna:

1. Probabilidad de terminar la siembra antes del 15/11, sobre los 20 climas y las réplicas de fallas.
2. Capacidad ociosa: horas paradas del equipo contratado, por causa (paso 4).
3. Margen: ingreso según el rinde, menos alquiler, sueldos y reparaciones (paso 5).

La mejor elección para cada superficie es la combinación de **mayor margen que cumple una probabilidad mínima** de terminar a tiempo, por ejemplo 90%.

**Propuesta.** El barrido principal (paso 7) cruza turnos (1 a 3) × máquinas (1 a 3) × superficie, más uno o dos tamaños de carro y de camión. Las demás variables de decisión y los factores inciertos van a la sensibilidad (paso 8), de a uno por vez. Cada factor que se agrega al barrido multiplica la cantidad de corridas. Por eso conviene elegir pocos y bien.

**Reglas del Monte Carlo (decididas el 2026-10-28).**

1. **Las mismas semillas para todos los escenarios.** Cada escenario se corre con los mismos 20 climas (`campaña` de 0 a 19) y con el mismo conjunto fijo de semillas de fallas (`semillaFallas` de 1 a R). Nunca se sortea una semilla distinta por escenario. Así, la diferencia entre dos escenarios se debe al escenario y no a que les tocaron fallas distintas, y se necesitan menos corridas para distinguirlos. Esta técnica se llama números aleatorios comunes. El modelo lo permite porque las fallas y la madurez usan generadores propios, con semillas que se derivan de `replica` y `tren` (parte 4.5). Hay un límite que se declara en el informe: la secuencia de tiempos entre fallas es la misma, pero cae en otro momento del calendario si el escenario cambia los turnos o la velocidad, porque se cuenta en horas de trabajo.
2. **No se prueban todas las combinaciones.** El barrido principal cruza solo los factores más importantes. El resto se estudia en la sensibilidad (paso 8), de a un parámetro por vez y con los demás en su valor base.

**Decisión (2026-10-28).** La cátedra pide comparar el sistema base contra **un** modelo alternativo, no una grilla de escenarios. La propuesta de cruzar turnos × máquinas × superficie queda descartada. El diseño está en la parte 4.5. Las variables de decisión que no entran ahí van a la sensibilidad (paso 8).

### 4.5 Sistema base contra sistema alternativo C (decidido el 2026-10-28)

**Los dos sistemas.** El alternativo cambia varias cosas a la vez. La pregunta es si conviene agrandarse.

| | Base | Alternativo C: arrendar más campo |
|---|---|---|
| Superficie | 12 lotes (1.253 ha), campo **propio** | 18 lotes (1.880 ha): los 12 propios y **6 arrendados** |
| Máquinas | 1 tren (máquina, carro y camión) | 2 trenes de 9 lotes |
| Jornada | 1 turno | 1 turno por máquina |

**Por qué no es obvio.** El alternativo tiene más campo, pero cada máquina siembra 9 lotes en vez de 12, así que puede terminar antes y perder menos rinde. A cambio paga arrendamiento, una segunda máquina y un segundo operario.

**Cómo se simula.**
- Dos parámetros nuevos en `Main`: `replica` (1 a 5) y `tren` (1 o 2). Las semillas se derivan de ellos y de la `campaña`: fallas = `replica + 5 × campaña + 100 × (tren − 1)` y madurez = `replica + 5 × campaña`. Así hay 100 metas de madurez distintas y 200 secuencias de fallas (100 por tren), y no solo 5. El base y el alternativo siguen usando las mismas semillas en cada par (`campaña`, `replica`). Con los valores por defecto (1 y 1) las semillas valen 1, como en la última corrida verificada. `semillaFallas` y `semillaMadurez` en 0 significan "derivar"; con otro valor lo fijan a mano.
- **Base:** 12 lotes, `tren = 1`. **Alternativo:** dos corridas de 9 lotes, `tren = 1` y `tren = 2`. Los dos trenes comparten el clima y la semilla de madurez (es el mismo cultivo) y tienen fallas distintas. El tren 1 del alternativo usa las mismas fallas que el base.
- El alternativo termina la siembra cuando termina el tren más lento, y su rinde suma los 18 lotes de los dos trenes.
- `ParametersVariation`: `campaña` 0 a 19 × `replica` 1 a 5 × `tren` 1 a 2 × `cantidadLotes` 9 y 12 = **400 corridas**. Las 100 de 12 lotes con `tren = 2` no se usan, a cambio de que sea un solo experimento. Quedan **100 observaciones por sistema**, emparejadas por (`campaña`, `replica`).

**Costos por campaña, en US$** (los calcula `herramientas/analizar_barrido.py` a partir del CSV; los supuestos se calibran para que el base dé margen positivo y se declaran en el informe):

| Rubro | Cálculo | Referencia |
|---|---|---|
| Ingreso | Σ rinde del lote × 104,4 ha × precio | 41 qq/ha, menos 25 kg/ha por día de atraso después del 15/11; 331 US$/t |
| Arrendamiento | qq/ha × ha arrendadas × precio | ~15 qq/ha, solo en el alternativo (626 ha) |
| Insumos por hectárea | US$/ha × superficie | ~350 US$/ha, supuesto |
| Flete y comercialización | % del ingreso | ~10%, supuesto |
| Costo fijo por tren | US$/campaña × trenes | Supuesto a calibrar (amortización, interés y seguro de máquina, carro y camión) |
| Operarios | salario anual × trenes | Escala UATRE en dólares |
| Combustible y mantenimiento | horas trabajadas × US$/h | ~25 l/h de gasoil más mantenimiento, supuesto |
| Reparaciones | fallas × US$/falla | Supuesto |

**Fundamento estadístico (28 y 29/10, contrastado con los TP 1.1, 2.2 y 3).**
- **Cantidad de observaciones.** En el TP 3 se usaron "30 réplicas independientes" por escenario con IC del 95%, y se eligió la política de menor costo promedio. Acá son 100 observaciones por sistema, más del triple, con la misma lógica de elección.
- **Independencia.** Las 100 observaciones no son independientes: son 20 climas históricos fijos con 5 semillas cada uno, y el clima domina el resultado. El IC de la diferencia de margen se calcula de dos maneras: con las 100 observaciones (como en el TP 3) y **por clima**, promediando las 5 semillas de cada año (20 diferencias independientes, t de Student con 19 grados de libertad). Si difieren, manda la segunda. Hay que declarar que 20 climas son menos que los 30 del TP 3; ampliar la serie de NASA POWER (desde 1981) es una opción, con el límite de 64 KB por literal de la JVM.
- **Proporción de siembras a tiempo.** Con ~90% y 100 observaciones hay unos 10 fracasos, suficientes para la aproximación normal. Los dos sistemas comparten semillas, así que se compara por pares (test de McNemar o IC de la diferencia de proporciones).
- **Gráficos del TP 3** que se replican en el análisis: media acumulada de la diferencia contra el número de observaciones, e histograma de las diferencias con su IC.
- **Validación sin teoría cerrada**, al estilo del TP 2.2: la media de `gddMeta` en las 100 corridas tiene que dar cerca de 1.900, y las fallas, cerca de las horas trabajadas divididas por `mtbfHoras`.

**Qué se compara.** El margen total y por hectárea, la probabilidad de terminar la siembra antes del 15/11 y, para decidir, la **diferencia de margen par a par** (misma `campaña` y `replica`) con su intervalo de confianza del 95%. Gana el sistema con mayor margen si el intervalo de la diferencia no incluye el 0.

---

## 5. Los pasos en detalle

### Paso 1. Siembra con reabastecimiento de semilla

**Objetivo.** Que la sembradora gaste semilla, que se le acabe y que dependa de una reposición. Medir el tiempo que espera.

**Diseño.** Semilla por el carro, con stock infinito en la cabecera. El 1b (stock finito repuesto por el camión) se descartó el 2026-10-19: el depósito queda infinito.

- **1a. Semilla por el carro, con stock infinito en la cabecera.**
  - `Combine` guarda `semilla` (kg en la tolva), `tasaSemilla` y `tUltimoSemilla`, igual que el grano. Un `actualizarSemilla()` integra el nivel por evento.
  - Consumo: `velocidad × ancho × densidad`. Con 7 km/h, 9 m y 0,007 kg/m² son 0,1225 kg/s, o 441 kg/h.
  - Cuando `semilla` baja de `umbralSemilla` (20%), `Combine` le manda `NEED_SEED` al carro.
  - El carro carga en la cabecera, viaja a la máquina y vuelca `min(carga, espacio)` de golpe, como el volcado de grano. Es conservativo por construcción. Después vuelve.
  - Si `semilla` llega a 0, la máquina para. Esto entra en `puedeTrabajar()`, que es el único punto de parada, sin mensajes nuevos.

**Parámetros nuevos (`Main`).** `densidadSiembra` (70 kg/ha), `capacidadSemilla` (4.000 kg), `umbralSemilla` (0,2).

**Elementos que se tocan.**
- `Combine`: variables y función de semilla, transición de aviso, condición en `puedeTrabajar()`, y la tasa de consumo en `tasaCosechaActual()`.
- `Cart`: estados nuevos para cargar semilla y entregarla, con guardas por `main.sembrando()` en las transiciones existentes que hoy asumen grano.
- `Main`: parámetros, y la auditoría de conservación de semilla.

**Auditoría.** Igual que con el grano: `semillaDespachada = semillaSembrada + combine.semilla + cart.semilla`. La `FUGA` de semilla tiene que dar ruido de punto flotante (~1e-9).

**Criterio de aceptación** (12 lotes, 1 turno, campaña 0):
- Se consumen 12 × 104,4 ha × 70 = 87.696 kg de semilla. Cada lote mide 104,4 ha y no 104, porque la máquina hace 145 hileras de 9 m (1.305 m de ancho).
- La `FUGA` de semilla es cercana a 0.
- Aparecen entregas de semilla en el log, una cada ~7,4 h de trabajo. Cada entrega es de unos 3.250 kg: lo que falta para llenar la tolva de 4.000 kg, que a esa altura tiene unos 800 kg. Salen entre 25 y 27 entregas.
- La tasa de consumo es 0,1225 kg/s (441 kg/h) con 7 km/h, 9 m y 70 kg/ha.
- La primera carga del carro es de 20.000 kg (se llena). Las siguientes son de solo lo que se entregó.
- Con los valores propuestos la máquina **no** espera semilla (0 h sin semilla). Eso confirma la parte 4.2.
- El día de fin de siembra no cambia más que por las esperas del carro (hoy: día 40).
- La cosecha sigue igual: 75 viajes, `FUGA` de grano ~0.

**Riesgos.** El carro hoy asume que el flujo es de la máquina hacia el carro. Las transiciones que cambian por modo son delicadas por las trampas de LIFO y de mensajes que se descartan (sección 5 del contexto). 

**Qué hace cada uno.** Claude escribe los scripts y la documentación. Luca corre `Simulation` y pega la consola.

### Paso 2. Fallas de máquina

**Objetivo.** Que la máquina se rompa mientras trabaja y quede detenida durante la reparación. Sin esto, todos los resultados son un límite optimista.

**Diseño.**
- Tercer statechart paralelo en `Combine`: `Operativa → Reparando → Operativa` (diseño de la sección 10 del contexto).
- La falla es exponencial con media `mtbfHoras`, en **horas de operación**. Una máquina parada no se rompe.
- Como la exponencial no tiene memoria, al reanudar el trabajo se vuelve a sortear el tiempo hasta la falla. Es estadísticamente equivalente a descontar el reloj consumido y evita contabilizarlo.
- La reparación es `triangular(0.5, 8, 2)` horas (mínimo, máximo, moda).
- Una falla se suma a `puedeTrabajar()` como un motivo más: `&& !reparando`.
- El `STOP` lo manda `Reparando` al entrar, no la transición de falla. Así no se hace `cancel()` sobre la transición que está disparando (sección 5 del contexto).
- Las fallas aplican a siembra y cosecha: es la misma máquina.

**Calibración.** El criterio viejo del contexto era "0,5 a 3 fallas por campaña", pensado para 21 horas de trabajo. Con 12 lotes la máquina trabaja unas 450 horas (199 de siembra y 253 de cosecha), así que:

| MTBF | Fallas esperadas | Tiempo perdido (reparación media de 3,5 h) |
|---|---|---|
| 40 h | ~11 | ~38 h (8% del tiempo de operación) |
| 100 h | ~4,5 | ~16 h (3%) |

El criterio nuevo es el porcentaje de tiempo perdido. **El MTBF necesita una fuente** (parte 4.3). Hasta tenerla, se usa 100 h y se barre en la sensibilidad.

**Elementos que se tocan.** `Combine` (statechart, `puedeTrabajar()`, rearmado de la falla al reanudar), `Main` (parámetros `mtbfHoras`, contadores de fallas y horas en reparación).

**Criterio de aceptación.**
- Con `mtbfHoras` muy grande (1e9), el resultado es idéntico al de hoy (siembra día 40, cosecha día 236). Esto prueba que el statechart nuevo no rompe lo que ya funciona. Como las fallas usan un generador propio, también `diaMadurez` queda igual.
- Con `mtbfHoras = 100`, el número de fallas de varias corridas tiene media cercana a 4,5.
- Nunca hay una falla con la máquina parada.
- La `FUGA` de grano y de semilla sigue en ~0 con las paradas por falla.

### Paso 3. Madurez por grados-día

**Objetivo.** Que el período de crecimiento dependa del clima de cada año, en vez de un sorteo `triangular(90, 150, 120)`.

**Qué son los grados-día.** Cada día se suma `temperatura media − 10 °C` (si da negativo, 0). Cuando el total llega a una meta, el cultivo madura. `gdd` ya se acumula en el tick diario, pero no se usa.

**Cambio.** La transición `Creciendo → Maduro` pasa de timeout `diasHastaMadurez` a condición `gdd >= gddObjetivo`. El tick diario ya llama a `cicloCultivo.onChange()`. Hay que poner `gdd = 0` al entrar a `Creciendo`.

**Calibración (calculada con las 20 campañas reales).** Siembra el día 40 (10/11):

| Meta `gddObjetivo` | Ciclo mediano | Rango | Madurez (día mediano) |
|---|---|---|---|
| 1.680 (actual) | 116 días | 97 a 139 | día 156 (5/3) |
| **1.900** | **137 días** | **112 a 166** | **día 177 (26/3)** |
| 2.100 | 158 días | 121 a 215 | día 198 (16/4) |

La meta de 1.680 hace madurar el cultivo en pleno marzo, antes de lo habitual para una siembra de noviembre. La de 1.900 da una madurez a fines de marzo. **Propuesta: 1.900**, a validar contra la fecha típica de cosecha de la zona (INTA o Bolsa de Cereales).

El sorteo actual tiene un rango de 60 días y la meta de 1.900 da un rango de 54, así que el ancho es parecido. Lo que cambia es el origen: la variabilidad sale del clima de cada campaña y no de un número inventado. Un año caluroso madura antes y uno fresco, después.

**Limitación a declarar.** El modelo usa solo temperatura, sin fotoperíodo. En la realidad, sembrar tarde acorta el ciclo, pero acá lo alarga: con siembra el día 60 y meta 2.100, el ciclo mediano llega a 196 días (con máximo de 303). Para el rango de fechas de siembra que se simula (hasta fines de noviembre) el efecto es chico.

**Riesgo.** Si en un año frío la suma no llega a la meta antes del 30/9, el cultivo nunca madura. Hay que detectarlo y registrarlo como observación "no maduró" (`diaMadurez = -1`), igual que ya se hace con `diaFinSiembra`.

**Criterio de aceptación.**
- La madurez de la campaña 0 coincide con el día calculado arriba para esa campaña.
- Las 20 campañas dan madurez entre 112 y 166 días después de la siembra, con meta 1.900.
- `diasHastaMadurez` deja de usarse. Se elimina, junto con los tres parámetros de la triangular, o se deja marcado como obsoleto.

### Paso 4. Causas de parada y contadores de carro y camión

**Objetivo.** Responder el resultado #2: en qué se pierde el tiempo y qué eslabón es el cuello de botella.

**Hoy.** `horasDetenida` mezcla todas las causas (noche, lluvia, tolva llena). No se puede saber cuál pesa más.

**Diseño.**
- Cuando la máquina para, se registra **una causa**, con esta prioridad: `falla`, `sin semilla`, `fuera de jornada`, `sin piso`, `esperando carro`. La prioridad se documenta porque varias causas pueden coincidir.
- Contadores por causa, en horas: `horasFalla`, `horasSinSemilla`, `horasJornada`, `horasSinPiso`, `horasEsperaCarro`. La suma tiene que dar `horasDetenida`.
- Para el carro y el camión: horas en cada estado (esperando, viajando, cargando, descargando) y su porcentaje de uso.
- `reportarPasada()` los imprime por pasada. El CSV del barrido agrega columnas.

**Criterio de aceptación.**
- Las causas suman `horasDetenida` con diferencia menor a 1e-6 h.
- Con 1 turno, `horasJornada` es ≈ 17,7 h por día de calendario trabajado (24 − 6,3).
- Los porcentajes de uso del carro y del camión son coherentes con el log: por ejemplo, el camión espera mucho porque cada viaje tarda 3,4 h en llenarse.

### Paso 5. Rinde según la fecha de siembra y costos

**Objetivo.** Responder el resultado #3: cuánto cuesta sembrar tarde y cuánto cuesta evitarlo.

**Decisiones (2026-10-28).**

1. **El modelo calcula lo físico y el script de análisis calcula la plata.** El modelo exporta al CSV el día en que termina cada lote, las horas trabajadas y detenidas por causa, las fallas y las horas del carro y del camión (sección 15 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md)). El rinde, los costos y el margen los calcula `herramientas/analizar_barrido.py` (paso 7). Así la sensibilidad a precios y costos (paso 8) se recalcula sin volver a simular, y el cálculo de N máquinas (parte 4.1) usa los mismos datos.
2. **Costo fijo por máquina y por campaña.** Si la maquinaria se pagara por hectárea, como cobran los contratistas, el costo sería el mismo con 1, 2 o 3 máquinas y no habría nada que comparar. Por eso cada máquina tiene un costo fijo por campaña, más un costo por hora trabajada (combustible) y por falla (reparación). Es una simplificación declarada.
3. **Los valores sin fuente se asumen.** Se eligen para que el margen dé positivo en general, se declaran como supuestos en el informe y se varían en la sensibilidad.
4. **La pérdida por cosechar tarde no entra en el margen base.** No hay un valor por día publicado. El CSV igual trae los días de cosecha de cada lote, así que se puede agregar en la sensibilidad.

**Rinde.**
- `rindeLote(k) = rindePotencial − perdidaDiaria × max(0, diaSiembraLote[k] − diaLimiteSiembra)`, por la superficie del lote (104,4 ha).
- Valores base: `rindePotencial` = 41 qq/ha (BCR GEA, soja de primera en zona núcleo, 2025/26) y `perdidaDiaria` = 25 kg/ha por día después del 15/11 (dato de zona núcleo sin publicación de INTA). En la sensibilidad: 15 y 36 kg/ha por día (INTA Córdoba e INTA Rafaela).

**Costos por campaña** (solo los que cambian entre escenarios; los que son iguales en todos, como la semilla o la cosecha por contratista, se cancelan al comparar):
- Máquinas: N × costo fijo por campaña.
- Operarios: N × `turnos` × salario mensual con cargas × meses que dura la siembra. Referencia: maquinista de cosecha, CCT UATRE, $1.892.406 por mes desde octubre 2026.
- Combustible: horas trabajadas × costo por hora.
- Reparaciones: fallas × costo por falla.
- Ingreso: `Σ rindeLote × precio`. Referencia: ~$560.000/t en la pizarra de Rosario, octubre 2026 (a confirmar con la BCR).
- Resultado: `margen = ingreso − costos`. Para cada superficie se busca la combinación de turnos y máquinas con mayor margen que cumpla la probabilidad objetivo. Por ejemplo, 90% de terminar antes del 15/11.

**Qué falta conseguir o asumir** (parte 4.3): costo fijo de una máquina por campaña, costo por hora de combustible, costo por falla y cargas sociales del salario.

**Criterio de aceptación.**
- Una siembra que termina antes del 15/11 tiene penalización 1,0.
- Una siembra que termina un mes más tarde pierde un porcentaje coherente con la fuente.
- El margen responde a costos y precios en el sentido esperado. Un alquiler más caro, por ejemplo, baja el número óptimo de máquinas.

### Paso 6. Crecimiento visual del cultivo (opcional)

Que el trigo 3D crezca durante `Creciendo`: altura o escala proporcional a `gdd / gddObjetivo`. Depende del paso 3. Falta verificar cómo se liga la escala de una `Figure3D` por código. Es solo presentación y no cambia resultados.

### Paso 7. Barrido final de Monte Carlo

**Objetivo.** Generar los resultados definitivos de los tres entregables.

**Diseño.**
- Experimento `ParametersVariation` con el diseño de la parte 4.5: `campaña` 0 a 19 × `replica` 1 a 5 × `tren` 1 y 2 × `cantidadLotes` 9 y 12, con `turnos = 1`. Son 400 corridas, de las que se usan 300.
- Se agregan al experimento los parámetros nuevos, como `mtbfHoras` y `densidadSiembra`. La lista de parámetros se congela al crear el experimento. Por eso hay que agregarlos al XML o recrearlo (aprendizaje 17 del contexto).
- `herramientas/analizar_barrido.py` (nuevo) lee `resultados.csv` y arma las tablas: probabilidad de terminar antes del 15/11, medianas, causas de parada y margen. Así el análisis se puede repetir y auditar.
- El script arma los dos sistemas: el base con las corridas de 12 lotes y `tren = 1`; el alternativo uniendo las dos corridas de 9 lotes de la misma `campaña` y `replica`.

**Criterio de aceptación.**
- No hay corridas sin fila en el CSV: el número de filas es igual al esperado.
- Hay 100 pares (`campaña`, `replica`) completos: una corrida del base y dos del alternativo cada uno.
- Con `mtbfHoras = 1e9`, el resultado coincide con el de antes de agregar fallas.
- El tren 1 del alternativo y el base tienen la misma semilla de fallas en cada par. Se comprueba en el script con las columnas `semillaFallas` y `semillaMadurez` del CSV.

### Paso 8. Sensibilidad

**Objetivo.** Mostrar cuánto cambia la respuesta con los parámetros más inciertos, en lugar de esconderlos.

Se varía **un parámetro por vez** y los demás quedan en su valor base. Se mide el cambio en la probabilidad de terminar a tiempo y en el margen:

| Parámetro | Valores | Por qué |
|---|---|---|
| `umbralPiso` | 15, 20, 25, 30 mm | Es el parámetro más influyente y no tiene valor publicado único |
| `mtbfHoras` | 40, 100, 200 h | Sin fuente definida |
| `velocidadSiembra` | 5, 7, 9 km/h | Rango habitual de siembra |
| `gddObjetivo` | 1.700, 1.900, 2.100 | Define la fecha de cosecha |

También se afinan las celdas de transición que quedaron sin resolver.

### Paso 9. Informe y cierre

- Regenerar `docs/ventana-siembra.html`: hoy tiene una advertencia de desactualizado. Se actualizan las partes de statecharts, variables, experimentos y resultados.
- Redactar el informe: modelo, supuestos con su fuente, resultados de los tres entregables y sensibilidad.
- Limpiar el repositorio: dejar uno o dos respaldos en `backups/` (hoy son 6, 2,4 MB), borrar `docs/CONTEXTO-TRASPASO.md.bak` y actualizar el README, que hoy tiene una línea.

---

## 6. Registro de avance

Se actualiza al terminar cada paso, con la fecha y el commit.

- [x] **Paso 0.** Docs actualizados y plan escrito. 2026-10-19.
- [x] Paso 1. Semilla. **1a verificado** el 2026-10-19: siembra con 12 lotes (27 entregas, `FUGA` 1e-11, 0 h sin semilla) y campaña completa con 1 lote (2 entregas, `FUGA` de semilla 0, `FUGA` de grano 1e-11). El 1b (stock finito) se descartó. Detalle en la sección 11 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
- [x] Paso 2. Fallas de máquina. **Implementado el 2026-10-19** en `feat/fallas`, con generador propio (`semillaFallas`). **Verificado con 1 lote** (sin fallas idéntico al de antes; con `mtbfHoras = 5`, 9 fallas y `FUGA` ~0) y **con 12 lotes el 2026-10-27** (`mtbfHoras = 100`: 5 fallas, 19,6 h de reparación, siembra el día 42, `FUGA` ~0). La media de fallas se mide en el barrido. Detalle en la sección 12 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
- [x] Paso 3. Madurez por grados-día. **Verificado el 2026-10-27** en `feat/gdd` (sale de `feat/fallas`), con meta 1.900: 1 lote madura el día 147 y 12 lotes el día 177, como se calculó. La cosecha de 12 lotes cierra el día 243, con `FUGA` 5,9e-9. Detalle en la sección 13 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
- [x] Paso 4. Causas de parada y contadores. **Verificado el 2026-10-27** en `feat/causas-parada`: con los parámetros de la corrida C repite los mismos eventos, las causas suman `horasDetenida` (diferencia 1e-11) y `otra` da 0. En la cosecha, la jornada es el 91% de lo detenido y la espera del carro, 21 h. Detalle en la sección 14 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
- [ ] Paso 5. Rinde y costos. **Diseño decidido el 2026-10-28** (costo fijo por máquina y por campaña; el modelo calcula lo físico y el script la plata). **Salidas del modelo implementadas** en `feat/rinde-costos`: días por lote y CSV de 55 columnas en UTF-8. **Verificado el 2026-10-28**: la fila es correcta y la siembra repite la corrida C. La cosecha cierra el día 251 por una falla más, y se asume que es por el cambio a AnyLogic 8.9.10. Todo el barrido tiene que correrse con una sola versión. Detalle en la sección 15 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
- [x] Paso 6. Crecimiento visual (opcional). **Tamaño hecho el 2026-10-27** en `feat/lluvia-visual`: escala de `crop3D` según `gdd / gddObjetivo`. **Color hecho el 2026-10-28** en `feat/color-cultivo`: el campo pasa de suelo sin sembrar a verde claro, verde intenso, ámbar maduro y rastrojo (opción 1 de la sección 6 bis de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md)). En la misma rama: color del campo con lluvia y sin piso, indicador de suelo y gotas en 2D y 3D (sección 6 bis de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md)).
- [ ] Paso 7. Barrido final. **2026-10-28:** se decidió comparar el sistema base contra el alternativo C (parte 4.5). En `feat/sistema-alternativo`: parámetros `replica` y `tren`, `ParametersVariation` de 400 corridas y CSV de 59 columnas (sección 17 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md)). **Verificado el 2026-10-29:** los valores por defecto repiten la sección 16 al dígito. **Pendiente:** escribir `herramientas/analizar_barrido.py`, asumir los costos sin fuente y correr el barrido.
- [ ] Paso 8. Sensibilidad.
- [ ] Paso 9. Informe y cierre.
