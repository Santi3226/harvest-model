# Plan de trabajo

Estado al 2026-10-19 (última actualización: paso 1a). Este documento es el plan vigente del proyecto: qué falta, en qué orden, cómo se decide cada cosa y cómo se comprueba que quedó bien. Cada paso tiene un criterio de aceptación que se verifica con una corrida, y un estado que se actualiza al terminarlo.

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
| 1 | Siembra con reabastecimiento de semilla | #2 | Ninguna | **1a verificado** (siembra y cosecha). 1b pendiente |
| 2 | Fallas de máquina | #1, #2, #3 | Ninguna | Pendiente |
| 3 | Madurez por grados-día (`gdd`) | #1 | Ninguna | Pendiente |
| 4 | Causas de parada y contadores de carro y camión | #2 | 1, 2 | Pendiente |
| 5 | Rinde según la fecha de siembra y costos | #3 | 1, 3, 4 | Pendiente |
| 6 | Crecimiento visual del cultivo | Ninguno | 3 | Opcional |
| 7 | Barrido final de Monte Carlo | #1, #2, #3 | 1 a 5 | Pendiente |
| 8 | Sensibilidad de los parámetros inciertos | #1, #3 | 7 | Pendiente |
| 9 | Informe, regenerar el HTML y limpiar el repo | Ninguno | Todos | Pendiente |

**Orden recomendado:** 1, 2, 3, 4, 5, 7, 8, 9. El paso 6 se hace si sobra tiempo. Los pasos 2 y 3 son independientes del 1 y se pueden intercambiar.

**Por qué este orden.** Los pasos 1 a 3 cambian los tiempos de la simulación. Por eso el barrido (paso 7) va después de todos. El paso 4 necesita que existan las causas de parada (semilla y fallas) para poder medirlas. El paso 5 necesita el día de siembra de cada lote (paso 1) y la madurez realista (paso 3).

---

## 4. Decisiones que cambian el alcance

Estas decisiones las tiene que conocer todo el grupo, porque son las que hay que defender frente al docente.

### 4.1 El modelo no puede simular dos máquinas

El modelo tiene una sola máquina con su carro y su camión. La pregunta del trabajo ("cuánta maquinaria alquilar") y el resultado #3 ("costo de maquinaria extra") necesitan comparar una máquina contra dos o tres.

**Propuesta:** tratar N máquinas como N trenes independientes (máquina, carro y camión), cada uno con `superficie / N`. Con el mismo clima para todos, la campaña termina cuando termina el tren más cargado. Eso equivale a simular `ceil(lotes / N)` lotes con una máquina. No hace falta código nuevo en el modelo: el análisis del barrido (paso 7) hace la cuenta y el costo se multiplica por N.

**Qué se pierde:** los trenes no comparten recursos (por ejemplo, un camión que atiende a dos máquinas). Se declara como simplificación. Redondear hacia arriba los lotes por tren es conservador.

**Alternativa descartada:** agregar una segunda instancia de `Combine`, `Cart` y `Truck` al modelo. Usa agentes del cupo de 10 de PLE, duplica el dibujo y el cableado de mensajes, y no aporta nada que la propuesta no dé.

### 4.2 Con valores realistas, la semilla casi no frena a la máquina

Una sembradora gasta unos 441 kg de semilla por hora (6,3 ha/h × 70 kg/ha). Con una tolva de 4.000 kg, eso son unas 9 horas de autonomía. Si el carro llega antes de que se vacíe, la máquina nunca espera.

Entonces el desabastecimiento solo aparece si **la reposición es lenta**. Por eso el paso 1 modela también el stock del depósito y el viaje del camión que lo repone. El resultado puede ser "la semilla no es un cuello de botella salvo que la reposición tarde más de X horas". Eso también es un resultado válido y se puede defender. El parámetro de reposición tiene que estar a la vista y barrerse en la sensibilidad.

### 4.3 Valores que hay que respaldar con una fuente

Ninguno de estos valores se puede inventar. Cada uno queda marcado en el modelo y en el informe como supuesto hasta tener la fuente:

| Valor | Hoy | Fuente a conseguir |
|---|---|---|
| Velocidad de siembra | 7 km/h | Ficha técnica de sembradora o ASABE D497.7 |
| Densidad de siembra | 70 kg/ha | INTA, recomendación para soja |
| Capacidad de la tolva de semilla | 4.000 kg | Ficha técnica de sembradora |
| MTBF y reparación | A definir | ASABE D497.7 u otro estudio de confiabilidad |
| Meta de grados-día | 1.900 | INTA o Bolsa de Cereales: fecha típica de cosecha de soja |
| Pérdida de rinde por siembra tardía | A definir | INTA, ensayos de fecha de siembra |
| Costos y precios | A definir | Ver paso 5 |

---

## 5. Los pasos en detalle

### Paso 1. Siembra con reabastecimiento de semilla

**Objetivo.** Que la sembradora gaste semilla, que se le acabe y que dependa de una reposición. Medir el tiempo que espera.

**Diseño (versión simple, en dos partes).**

- **1a. Semilla por el carro, con stock infinito en la cabecera.**
  - `Combine` guarda `semilla` (kg en la tolva), `tasaSemilla` y `tUltimoSemilla`, igual que el grano. Un `actualizarSemilla()` integra el nivel por evento.
  - Consumo: `velocidad × ancho × densidad`. Con 7 km/h, 9 m y 0,007 kg/m² son 0,1225 kg/s, o 441 kg/h.
  - Cuando `semilla` baja de `umbralSemilla` (20%), `Combine` le manda `NEED_SEED` al carro.
  - El carro carga en la cabecera, viaja a la máquina y vuelca `min(carga, espacio)` de golpe, como el volcado de grano. Es conservativo por construcción. Después vuelve.
  - Si `semilla` llega a 0, la máquina para. Esto entra en `puedeTrabajar()`, que es el único punto de parada, sin mensajes nuevos.
- **1b. Stock finito en la cabecera, repuesto por el camión.**
  - La cabecera tiene `stockSemilla`. El carro lo gasta al cargar.
  - Cuando baja de un umbral, el camión sale al depósito, tarda `tViajeInsumos` y trae su carga.
  - Con 12 lotes se necesitan unas 87 t de semilla (12 × 7,28 t), o sea 2 viajes de 50 t.

**Parámetros nuevos (`Main`).** `densidadSiembra` (70 kg/ha), `capacidadSemilla` (4.000 kg), `umbralSemilla` (0,2), `stockInicialSemilla` y `tViajeInsumos` (parte 1b).

**Elementos que se tocan.**
- `Combine`: variables y función de semilla, transición de aviso, condición en `puedeTrabajar()`, y la tasa de consumo en `tasaCosechaActual()`.
- `Cart`: estados nuevos para cargar semilla y entregarla, con guardas por `main.sembrando()` en las transiciones existentes que hoy asumen grano.
- `Truck` (solo 1b): estado de viaje al depósito.
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
- Con `tViajeInsumos` muy grande, la máquina espera semilla y el contador lo muestra.

**Riesgos.** El carro hoy asume que el flujo es de la máquina hacia el carro. Las transiciones que cambian por modo son delicadas por las trampas de LIFO y de mensajes que se descartan (sección 5 del contexto). Por eso 1a y 1b se prueban por separado.

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
- Con `mtbfHoras` muy grande (1e9), el resultado es idéntico al de hoy (siembra día 40, cosecha día 236). Esto prueba que el statechart nuevo no rompe lo que ya funciona.
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

**Diseño del rinde.**
- Cada lote tiene su propio día de siembra: `diaSiembraLote[k]`. Se guarda en `onCompleted()`.
- `penalizacionPorFecha(dia)` devuelve el rinde relativo (1,0 hasta cierta fecha y menor después), armada como tabla de búsqueda a partir de ensayos de INTA.
- `rindeEfectivo = Σ rindePotencial × superficieLote × penalizacion(diaSiembraLote[k])`.
- También una pérdida por demora de cosecha: cada día que el grano queda en el campo después de la madurez pierde un porcentaje. El valor se toma de una fuente.

**Diseño de los costos** (por campaña):
- Máquinas: alquiler por hectárea o por hora, por N trenes (parte 4.1).
- Operarios: salario por turno según el régimen agrario (Ley 26.727), por los días trabajados.
- Combustible y reparaciones: costo por hora y costo por falla.
- Ingreso: `rindeEfectivo × precio de pizarra`.
- Resultado: `margen = ingreso − costos`. Para cada superficie se busca la combinación de turnos y máquinas con mayor margen que cumpla la probabilidad objetivo. Por ejemplo, 90% de terminar antes del 15/11.

**Qué hay que conseguir antes** (parte 4.3): curva de rinde contra fecha de siembra, precio de la soja, costo de alquiler de siembra y cosecha, salario del operario y costo de combustible. Los datos los pone el grupo o se buscan en fuentes públicas (sección 11 del contexto: INTA, Bolsa de Comercio de Rosario, consiagro).

**Criterio de aceptación.**
- Una siembra que termina antes del 15/11 tiene penalización 1,0.
- Una siembra que termina un mes más tarde pierde un porcentaje coherente con la fuente.
- El margen responde a costos y precios en el sentido esperado. Un alquiler más caro, por ejemplo, baja el número óptimo de máquinas.

### Paso 6. Crecimiento visual del cultivo (opcional)

Que el trigo 3D crezca durante `Creciendo`: altura o escala proporcional a `gdd / gddObjetivo`. Depende del paso 3. Falta verificar cómo se liga la escala de una `Figure3D` por código. Es solo presentación y no cambia resultados.

### Paso 7. Barrido final de Monte Carlo

**Objetivo.** Generar los resultados definitivos de los tres entregables.

**Diseño.**
- Experimento `ParametersVariation` con `campania` de 0 a 19, `cantidadLotes` y `turnos`. Con el paso 2 hay aleatoriedad (las fallas), así que se hacen **varias réplicas** por combinación, con semillas distintas. La madurez por grados-día no suma aleatoriedad: depende solo del clima de la campaña.
- Se agregan al experimento los parámetros nuevos, como `mtbfHoras` y `densidadSiembra`. La lista de parámetros se congela al crear el experimento. Por eso hay que agregarlos al XML o recrearlo (aprendizaje 17 del contexto).
- `herramientas/analizar_barrido.py` (nuevo) lee `resultados.csv` y arma las tablas: probabilidad de terminar antes del 15/11, medianas, causas de parada y margen. Así el análisis se puede repetir y auditar.
- Las máquinas extra se calculan en el análisis (parte 4.1).

**Criterio de aceptación.**
- No hay corridas sin fila en el CSV: el número de filas es igual al esperado.
- La tabla de probabilidad tiene sentido: sube con los turnos y baja con la superficie.
- Con `mtbfHoras = 1e9`, el resultado coincide con el de antes de agregar fallas.

### Paso 8. Sensibilidad

**Objetivo.** Mostrar cuánto cambia la respuesta con los parámetros más inciertos, en lugar de esconderlos.

Se varía **un parámetro por vez** y los demás quedan en su valor base. Se mide el cambio en la probabilidad de terminar a tiempo y en el margen:

| Parámetro | Valores | Por qué |
|---|---|---|
| `umbralPiso` | 15, 20, 25, 30 mm | Es el parámetro más influyente y no tiene valor publicado único |
| `mtbfHoras` | 40, 100, 200 h | Sin fuente definida |
| `velocidadSiembra` | 5, 7, 9 km/h | Rango habitual de siembra |
| `tViajeInsumos` | 1, 4, 12 h | Define si la semilla es o no un cuello de botella |
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
- [ ] Paso 1. Semilla. **1a verificado** el 2026-10-19: siembra con 12 lotes (27 entregas, `FUGA` 1e-11, 0 h sin semilla) y campaña completa con 1 lote (2 entregas, `FUGA` de semilla 0, `FUGA` de grano 1e-11). 1b pendiente. Detalle en la sección 11 de [CAMBIOS-2026-10.md](CAMBIOS-2026-10.md).
- [ ] Paso 2. Fallas de máquina.
- [ ] Paso 3. Madurez por grados-día.
- [ ] Paso 4. Causas de parada y contadores.
- [ ] Paso 5. Rinde y costos.
- [ ] Paso 6. Crecimiento visual (opcional).
- [ ] Paso 7. Barrido final.
- [ ] Paso 8. Sensibilidad.
- [ ] Paso 9. Informe y cierre.
