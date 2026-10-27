# Cambios de octubre 2026: ciclo completo de campaña y clima anual

Este documento explica qué cambió en el modelo el 5 y el 19 de octubre de 2026. También explica cómo funciona ahora y por qué se decidió así. Está pensado para que cualquiera del grupo pueda leerlo, entender el código y defender las decisiones frente al docente.

No hace falta haber seguido la conversación en la que se hicieron los cambios. Sí conviene conocer lo básico de AnyLogic (agente, statechart, estado, transición). Esos términos están explicados en la Parte 2 de [ventana-siembra.html](ventana-siembra.html).

**Estado:** la siembra y el clima anual están verificados con una corrida de `Simulation` (sección 8). La semilla con reposición del carro (paso 1a, sección 11) está verificada en la siembra y en la cosecha. El stock finito repuesto por el camión (paso 1b) se descartó: el depósito queda infinito.

---

## 1. Resumen

Antes de este cambio, la campaña tenía un problema de fondo: **la máquina que recorría el lote en octubre era una cosechadora**, y el modelo llamaba "siembra" a esa pasada. El campo seguía en el estado `SinSembrar` durante todo el recorrido. Recién después crecía el cultivo y la misma máquina volvía a cosechar.

Ahora cada corrida simula **una campaña completa y coherente**:

| | Antes | Ahora |
|---|---|---|
| Pasada de octubre | La cosechadora cosechaba grano en un campo sin sembrar | La máquina **siembra**: recorre los lotes sin mover grano |
| Crecimiento | Empezaba al terminar esa pasada | Empieza al terminar la siembra (igual) |
| Cosecha | Segunda pasada, leía el clima de octubre (bug) | Pasada al madurar el cultivo, con el clima de esos días |
| Fin de la corrida | El barrido cortaba al terminar la primera pasada | Termina al cerrar la cosecha (estado `Cosechado`) |
| Clima | 212 días por campaña (1/10 al 30/4) | Año completo, 365 o 366 días (1/10 al 30/9) |
| Máquinas | Una cosechadora | La misma máquina, con dos modos: siembra y cosecha |

---

## 2. El ciclo de una campaña

### El statechart `cicloCultivo` (en `Main`)

```
  ●
  │
  ▼
SinSembrar ──[siembraCompleta]──► Creciendo ──[timeout diasHastaMadurez]──► Maduro ──[cosechaCompleta]──► Cosechado
 (siembra)                         (la máquina                               (cosecha)                      (fin)
                                    en el galpón)
```

Qué pasa en cada estado:

| Estado | Qué hace la máquina | Qué dispara la salida |
|---|---|---|
| `SinSembrar` | Siembra todos los lotes, uno por uno | `onCompleted()` pone `siembraCompleta = true` al terminar el último lote |
| `Creciendo` | Queda en el galpón | Pasan `diasHastaMadurez` días, sorteados con `triangular(90, 150, 120)` |
| `Maduro` | Cosecha todos los lotes. El grano viaja tolva → carro → camión → silo | `onCompleted()` pone `cosechaCompleta = true` al terminar el último lote |
| `Cosechado` | Nada. Es el estado final | No tiene salida |

### Cómo se ve en el tiempo (valores por defecto: 12 lotes, 1 turno, campaña 2005/06)

```
día 0 (1/10) ──── siembra ────► ~día 35 ──── crecimiento (90–150 días) ────► ~día 155 ──── cosecha ────► ~día 200
                (DENTRO si ≤ 45)                                              (madurez)                   (fin)
```

Los números son aproximados. Los reales salen de la corrida.

### Por qué una corrida es una sola campaña

Antes, el ciclo volvía de `Maduro` a `SinSembrar` y empezaba otra vuelta. Eso obligaba a reiniciar el contador de días (`diaCampania = 0`), y ese reinicio hacía que la cosecha leyera el clima de octubre. Con un estado final (`Cosechado`):

- El día del modelo coincide siempre con el día del calendario. El día 0 es el 1/10.
- Cada corrida del barrido es una observación independiente: una campaña climática, de punta a punta.
- No hace falta código de reinicio, que era una fuente de errores.

---

## 3. Una máquina, dos modos

### La decisión

La misma máquina (el agente `Combine`) siembra y cosecha. El modo no es una variable aparte, sino que **se deduce del estado del campo**: si el campo está `SinSembrar`, la máquina siembra.

```java
// Main.sembrando()
return inState( SinSembrar );
```

Por qué así y no con un agente "Sembradora" nuevo:

- **Límite de PLE:** la versión gratuita de AnyLogic permite 10 tipos de agente. Hoy usamos 4.
- **Se reusa todo lo que ya funciona:** el recorrido por hileras, las paradas de `puedeTrabajar()`, los turnos y los contadores de horas.
- **Una sola fuente de verdad:** el modo sale del estado del campo. No hay una bandera de modo que pueda quedar desincronizada.

La alternativa descartada fue un agente nuevo, que duplicaba unos 30 estados y transiciones, y cualquier arreglo había que hacerlo dos veces.

### Qué cambia según el modo

| | Sembrando | Cosechando |
|---|---|---|
| Velocidad de labor | `velocidadSiembra` = 7 km/h | `velocidadCosecha` = 5,5 km/h |
| Ancho de labor | 9 m (`RowWidth`) | 9 m (`RowWidth`) |
| Grano que entra a la tolva | 0 | velocidad × ancho × `HarvestDensity` |
| Carro y camión | Quietos | Trabajan |
| Para por lluvia y jornada | Sí | Sí |

Capacidad teórica: sembrando, 7 km/h × 9 m = 6,3 ha/h, o sea unas 16,5 h por lote de 104 ha. Cosechando, 5,5 km/h × 9 m ≈ 4,95 ha/h, o sea 21,1 h por lote. Este último es el valor que ya estaba calibrado.

### Dónde está en el código

**1. Cuándo sale la máquina del galpón.** La transición `Parked → GoingToField` de `Combine` tiene la condición `main.laborPendiente()`:

```java
// Main.laborPendiente()
return ( inState( SinSembrar ) && !siembraCompleta )
    || ( inState( Maduro )     && !cosechaCompleta );
```

Es decir: sale si hay un campo para sembrar o uno maduro para cosechar, y todavía quedan lotes. Las condiciones de AnyLogic no se reevalúan solas cuando cambia una variable de otro agente. Por eso el tick horario de `Main` (`tickDiario`) y el entry de `Maduro` llaman a `combine.moveControl.onChange()`.

**2. Velocidad según el modo.** En el entry de `GoingToField` (`Combine`):

```java
setSpeed( main.sembrando() ? main.velocidadSiembra : main.velocidadCosecha, KPH );
```

**3. Sembrando no entra grano.** En `Combine.tasaCosechaActual()`:

```java
return ( trabajando && !main.sembrando() ) ? harvestRate() / second() : 0;
```

Esta función es el único lugar del que sale la tasa de grano. Si da 0, la tolva no se llena y nunca se llama al carro. Así, el carro y el camión quedan quietos sin tocar su código.

---

## 4. Cómo termina cada pasada

`Combine` llama a `Main.onCompleted()` cada vez que termina **un lote**. Esa función cuenta los lotes y, cuando están todos, cierra la pasada:

```java
lotesCompletados++;
if ( lotesCompletados < cantidadLotes ) return;   // faltan lotes: la máquina vuelve a salir sola
lotesCompletados = 0;                             // la próxima pasada cuenta desde cero
if ( sembrando() ) {
    diaFinSiembra = diaCampania;                  // ← respuesta del entregable #1
    traceln( "=== SIEMBRA TERMINADA | ... DENTRO/FUERA de la ventana ..." );
    reportarPasada();
    siembraCompleta = true;
} else {
    diaFinCosecha = diaCampania;
    traceln( "=== COSECHA TERMINADA | ... dias desde la madurez ..." );
    reportarPasada();
    auditarMasa();                                // conservación del grano
    cosechaCompleta = true;
    if ( terminarAlCerrarCampania ) { getEngine().finish(); return; }
}
cicloCultivo.onChange();                          // para que el ciclo vea la bandera nueva
```

- **`reportarPasada()`** (nueva) imprime las horas trabajadas y detenidas, el uso, los viajes de camión y los días sin piso **de esa pasada**. Después guarda una "foto" de los acumulados (`baseTrabajando`, `baseDetenida`, `baseViajes` y `baseSinPiso`), para que la pasada siguiente reporte solo lo suyo.
- **`auditarMasa()`** ahora solo verifica la conservación del grano. Antes también imprimía los contadores, y esa parte pasó a `reportarPasada()`.
- **`diaLimiteSiembra`** (parámetro, 45 = 15/11) define la ventana de siembra. Antes el 45 estaba escrito directo en el código.

---

## 5. Clima de año completo

### De dónde salen los datos

Son los mismos datos que antes: **NASA POWER** (reanálisis MERRA-2), punto −33,0 / −61,0 (zona de Rosario). Son 20 campañas, de 2005/06 a 2024/25. La diferencia es que ahora cada campaña va del **1/10 al 30/9**: 365 días, o 366 si incluye un 29 de febrero. Antes iba solo hasta el 30/4 y la cosecha se quedaba sin clima.

La descarga es una sola llamada, sin registro:

```
https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=ag&longitude=-61.0&latitude=-33.0&start=20051001&end=20250930&format=CSV
```

El CSV crudo quedó guardado en [`datos/nasa_power_rosario_2005-2025.csv`](../datos/nasa_power_rosario_2005-2025.csv), para que se pueda auditar.

### Cómo se calculan las tres series

| Serie | Variable del modelo | Cálculo |
|---|---|---|
| Lluvia [mm/día] | `climaLluvia` | `PRECTOTCORR`, redondeada a 1 decimal |
| Temperatura media [°C] | `climaTmedia` | (Tmax + Tmin) / 2, redondeada a 1 decimal |
| ET0 [mm/día] | `climaEt0` | Hargreaves (FAO-56, ec. 52): 0,0023 · (Tmedia + 17,8) · √(Tmax − Tmin) · Ra · 0,408 |

`Ra` es la radiación que llega al tope de la atmósfera. Depende solo de la latitud y del día del año (FAO-56, ecuaciones 21 a 25). La ET0 (evapotranspiración de referencia) es cuánta agua pierde el suelo por día. El modelo la usa para secar la capa superficial.

### El script

[`herramientas/clima_nasa.py`](../herramientas/clima_nasa.py) hace todo el proceso:

```bash
python3 herramientas/clima_nasa.py              # baja los datos si falta el CSV y los inyecta en el .alp
python3 herramientas/clima_nasa.py --verificar  # solo compara, no escribe
```

Cada serie se guarda en el `.alp` como un único texto (`"día,día,...;día,día,..."`: días separados por coma y campañas por punto y coma). `Main.cargarClima()` la convierte en arreglos al arrancar. Se guarda como texto y no como arreglo porque AnyLogic inicializa todas las variables en un solo método. Java no admite métodos de más de 64 KB de código. La serie más grande mide 36 KB.

### Cómo se validó

- **Reproducibilidad:** el script reproduce **byte a byte** las series anteriores en los primeros 212 días. Los datos viejos no cambiaron: solo se agregaron días.
- **Contra la climatología de Rosario:** la lluvia anual mediana es de 1.056 mm (rango de 596 a 1.500). La temperatura media es de 25,9 °C en enero y de 10,6 °C en julio.

Salvedad para declarar en el informe: es reanálisis satelital, no una estación meteorológica. La celda mide unos 50 × 60 km, así que promedia y suaviza los extremos de lluvia. Por eso subestima un poco los días sin piso.

---

## 6. Catálogo de lo que se agregó o cambió

### Parámetros nuevos (`Main`)

| Parámetro | Valor | Qué es |
|---|---|---|
| `velocidadSiembra` | 7 km/h | Velocidad de la máquina sembrando |
| `velocidadCosecha` | 5,5 km/h | Velocidad cosechando. Antes estaba fija en el agente `Combine`. Se mantuvo el valor calibrado |
| `diaLimiteSiembra` | 45 | Último día de la ventana de siembra (día 0 = 1/10, 45 = 15/11) |

Parámetro modificado: **`cantidadLotes`**, que por defecto pasó de 40 a **12** (1.248 ha). Con 40 lotes y 1 turno, la cosecha no entraba en el año. El barrido no se ve afectado, porque fija su propio valor.

### Variables nuevas o renombradas (`Main`)

| Variable | Tipo | Qué guarda |
|---|---|---|
| `cosechaCompleta` | boolean | `true` cuando se cosecharon todos los lotes. Hace de pareja de `siembraCompleta` |
| `diaMadurez` | int | Día en que el cultivo maduró (−1 si no maduró) |
| `diaFinCosecha` | int | Día en que terminó la cosecha (−1 si no terminó) |
| `horasTrabajando` | double | Antes `horasCosechando`. Se renombró porque ahora también cuenta la siembra |
| `baseTrabajando` | double | Antes `baseCosechando` |

`siembraCompleta` y `diaFinSiembra` ya existían, pero **recuperaron su significado real**: antes marcaban el fin de una pasada de cosechadora, y ahora marcan el fin de la siembra.

### Funciones nuevas (`Main`)

| Función | Devuelve | Qué hace |
|---|---|---|
| `sembrando()` | boolean | `true` si el campo está `SinSembrar` (modo siembra) |
| `laborPendiente()` | boolean | `true` si hay un campo para sembrar o cosechar y quedan lotes |
| `reportarPasada()` | nada (`void`) | Imprime los contadores de la pasada y toma la foto de los acumulados |

### Statechart `cicloCultivo`

- El punto de entrada vuelve a `SinSembrar`.
- `SinSembrar → Creciendo` (condición `siembraCompleta`) se restauró.
- `Maduro → Cosechado` (condición `cosechaCompleta`) reemplazó a `Maduro → SinSembrar`, que tenía el reinicio de campaña.
- **Estado nuevo `Cosechado`**, que es el estado final.
- Entry de `SinSembrar`: baja la velocidad de la animación (la máquina trabaja).
- Entry de `Creciendo`: además de sortear los días hasta la madurez, imprime `Siembra cerrada el dia N — el cultivo crece M dias`.
- Entry de `Maduro`: guarda `diaMadurez`, toma la foto de `diasSinPiso` y avisa a la máquina. La foto evita que los días de lluvia del crecimiento cuenten como de la cosecha.

### `Combine`

- `Parked → GoingToField`: la condición pasó a `main.laborPendiente()`.
- Entry de `GoingToField`: fija la velocidad según el modo.
- `tasaCosechaActual()`: devuelve 0 sembrando.

### Experimento `ParametersVariation`

- **Stop time: 52 semanas** (antes 31). La corrida ahora termina al cerrar la cosecha, y eso puede pasar en cualquier momento del año.
- `resultados.csv` agrega dos columnas: `lotes;turnos;campania;diaFinSiembra;diaMadurez;diaFinCosecha`.

---

## 6 bis. Animación: qué se ve y por qué

El campo dibujado representa **un lote de 104 ha**. La máquina lo recorre una vez por lote, y al terminar la animación vuelve a empezar con el lote siguiente. Con 12 lotes hay 12 pasadas de siembra y 12 de cosecha. Las horas de la corrida lo confirman: 198,9 h de siembra son 12 × 16,57 h.

Para ver el avance total sin cambiar la geometría, se agregaron tres elementos al dibujo de `Main`. Así tampoco cambian los tiempos del carro, que viaja a 15 km/h entre la máquina y la cabecera.

| Elemento | Qué muestra |
|---|---|
| `textAvance` | Debajo del campo: `SIEMBRA: lote 5 de 12 \| dia 31 (1248 ha)`. Cambia a `CRECIMIENTO`, `COSECHA: lote N de M` y `CAMPO COSECHADO` según el estado |
| `rectLote` | Un cuadradito de 14 px por lote (`cantidadLotes` réplicas, 20 por fila). El lote en curso lleva borde negro |
| `crop3D` (cambio) | El trigo ahora depende del estado del campo |

Colores de `rectLote`: gris = sin sembrar, marrón = sembrado, verde = creciendo, lima = maduro, dorado = cosechado.

Visibilidad del trigo (`crop3D`):
- `SinSembrar`: el trigo aparece detrás de la máquina, que va sembrando.
- `Creciendo`: se ve todo el lote.
- `Maduro`: el trigo desaparece detrás de la máquina, que va cosechando.
- `Cosechado`: no se ve nada.

Antes, la regla solo miraba la posición de la máquina. Por eso, durante la siembra, se veía un campo ya crecido que se iba "cosechando".

**Alternativa descartada:** dibujar un campo con la superficie total, por ejemplo de 3,5 × 3,5 km para 12 lotes. La máquina haría una sola pasada. Tiene dos problemas. Cambia las distancias del carro y, con eso, los tiempos de espera ya validados. Además, las 4.000 plantas del trigo quedarían muy ralas. Si el docente quiere ver el campo entero, se puede hacer como una vista aparte.

### Velocidad de la animación

El experimento `Simulation` corre en tiempo real con escala: cada segundo real equivale a una cantidad fija de tiempo simulado, y el modelo la cambia según el estado del campo. Este ajuste no cambia ningún resultado.

| Estado | Escala | Duración aproximada (12 lotes, 1 turno) |
|---|---|---|
| `SinSembrar` | `0.5 * day()` (0,5 días por segundo) | Unos 80 s para 40 días de siembra |
| `Creciendo` | `1 * week()` | Segundos: la máquina está quieta |
| `Maduro` | `0.05 * day()` | Unos 15 minutos para 70 días de cosecha |
| `Cosechado` | No aplica | La corrida termina al cerrar la cosecha (`terminarAlCerrarCampania = true` desde el 19/10) |

La siembra usaba `0.05 * day()` y tardaba unos 13 minutos. Se subió a `0.5 * day()` para poder verla completa. Si la cosecha se hace lenta, se sube de la misma forma en el entry de `Maduro`. Se puede cambiar también durante la corrida, con el control de velocidad de la ventana de simulación.

Respaldo previo al cambio visual: `backups/2026-10-05-pre-visual-lotes.alp`. Posterior: `backups/2026-10-05-visual-lotes.alp`.

---

## 7. Decisiones de modelado (para la defensa)

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Una máquina con dos modos | Un agente "Sembradora" nuevo | Límite de 10 tipos de agente en PLE. Reusa la lógica de parada, jornada y turnos ya probada. No duplica código |
| El modo sale del estado del campo (`inState(SinSembrar)`) | Una variable `modo` aparte | Una sola fuente de verdad: no puede quedar desincronizada |
| Una corrida = una campaña, con estado final `Cosechado` | Ciclo que vuelve a `SinSembrar` | El reinicio de días causaba que la cosecha leyera el clima de octubre. Además, cada corrida es una observación independiente |
| Siembra sin logística (versión 1) | Modelar la semilla desde el principio | Permite probar el ciclo nuevo aislado. Si algo falla, se sabe que es el ciclo y no la logística. La semilla entra en la versión 2 |
| Mismo ancho de labor (9 m) en los dos modos | Anchos distintos | Una sembradora de 17 surcos a 52,5 cm mide unos 9 m, igual que la plataforma. Además, el ancho define la geometría de las hileras en la animación |
| Velocidad de siembra de 7 km/h | Usar la misma velocidad que la cosecha | Rango habitual de siembra directa: 6 a 8 km/h. **Hay que respaldarlo con una fuente** (por ejemplo, ASABE D497.7 o INTA) |
| La madurez sigue siendo `triangular(90,150,120)` desde el fin de la siembra | Grados-día (`gdd`) | Cambiar una cosa por vez. Los grados-día son el próximo paso |
| La ventana de siembra es un parámetro (`diaLimiteSiembra`) | Fija en el código | Permite el análisis de sensibilidad (por ejemplo, ventana hasta el 30/11) |
| Clima por día de calendario, con el 29/2 incluido | Recortar los años bisiestos a 365 días | El día del modelo coincide siempre con la fecha real |

---

## 8. Cómo verificar los cambios

1. Si AnyLogic está abierto con el modelo, cerralo **sin guardar** y volvé a abrirlo. Si no, el IDE puede pisar el archivo con la versión que tiene en memoria.
2. Corré el experimento `Simulation` (campaña 0, 12 lotes, 1 turno).
3. En la consola deberías ver, en este orden:

```
CLIMA dia 1 | ...                                        ← el clima avanza desde el 1/10
### MAQUINA PARA / REANUDA ...                            ← siembra: para de noche y con lluvia
                                                            (tolvaLlena siempre false, sin VIAJE)
=== SIEMBRA TERMINADA | superficie=1248 ha | dia ~35 | DENTRO de la ventana (dia limite 45)
SIEMBRA | trabajando=~198 h | ... | viajes camion=0 | ...
Siembra cerrada el dia ~35 — el cultivo crece ~120 dias
Cultivo maduro el dia ~155 — listo para cosecha
### MAQUINA PARA ... tolvaLlena=true ...                  ← cosecha: ahora sí se llena la tolva
VIAJE 1 | ...                                            ← y salen camiones
=== COSECHA TERMINADA | campania 1 | dia ~200 | ~45 dias desde la madurez
COSECHA | trabajando=~253 h | ... | viajes camion=~75 | ...
AUDITORIA ... FUGA=~0                                    ← el grano se conserva
Campo cosechado el dia ~200 — fin de campania
```

### Resultado de la corrida de verificación (campaña 0, 12 lotes, 1 turno)

| Qué se comprobó | Esperado | Medido |
|---|---|---|
| Siembra sin grano | 0 viajes, `tolvaLlena=false` | 0 viajes, `tasa=0.0` en todas las paradas |
| Horas de siembra | 12 × 16,57 h = 198,9 h | 198,86 h |
| Fin de siembra | Dentro del día 45 | Día 40, **DENTRO** (5 días sin piso) |
| Crecimiento | Máquina quieta | Sin ningún `PARA` ni `REANUDA` del día 40 al 168 |
| Madurez | `triangular(90,150,120)` desde el fin de siembra | 127 días, madura el día 168 |
| Horas de cosecha | 12 × 21,09 h = 253,1 h | 253,09 h |
| Viajes de camión | 12 × 313,2 t ÷ 50 t = 75 | 75 (el resumen dice 74, ver abajo) |
| Conservación de grano | `FUGA` cerca de 0 | 5,1e-9 kg sobre 3.758 t |
| Fin de campaña | Estado `Cosechado` | Día 236, 68 días después de la madurez, 16 días sin piso |

**El resumen dice 74 viajes y el log 75.** El camión del viaje 75 termina de descargar *después* de que la cosecha cierra. Su grano está en `enSistema` de la auditoría, por eso la `FUGA` da cero. No es un bug, pero conviene saberlo si alguien pregunta.

**Uso de la máquina:** siembra 20% y cosecha 15%. Con 1 turno la máquina puede trabajar como máximo 6,3 h de 24 (26%). El resto es noche, lluvia y esperas del carro.

---

## 9. Qué quedó pendiente o afectado

- **`resultados.csv` es del modelo anterior.** Mide la pasada de cosechadora de octubre. El barrido hay que **rehacerlo** con el modelo nuevo. Ahora tarda más, porque cada corrida simula el año completo.
- **El barrido no puede variar los parámetros nuevos.** La lista de parámetros de un `ParametersVariation` se congela al crearlo. Por eso `velocidadSiembra`, `velocidadCosecha` y `diaLimiteSiembra` corren con su valor por defecto. Para variarlos, hay que recrear el experimento.
- **[ventana-siembra.html](ventana-siembra.html) quedó desactualizado** en la Parte 6 (statecharts), la Parte 9 (catálogo de variables), la Parte 11 (experimentos) y la Parte 13 (lo que falta). Mientras tanto vale este documento.
- **Reabastecimiento de semilla:** el paso 1a (carro con stock infinito) está hecho, ver la sección 11. El 1b (stock finito en la cabecera, repuesto por el camión) se descartó el 19/10: la semilla no es un cuello de botella con estos valores y se declara como supuesto.
- **Grados-día:** pasar `Creciendo → Maduro` a la condición `gdd >= gddObjetivo`, y recalibrar `gddObjetivo` para que la madurez caiga entre marzo y abril.
- **Meta de la cosecha:** definir contra qué se mide la cosecha. Por ejemplo, "cosechar dentro de los 30 días desde la madurez". `diaFinCosecha − diaMadurez` ya se imprime y se guarda en el CSV.

---

## 10. Registro de cambios y respaldos

Todos los cambios se hicieron por script sobre el `.alp`, con copia previa en `backups/`:

| Respaldo | Estado que guarda |
|---|---|
| `backups/2026-10-05-pre-ciclo-cosecha.alp` | Modelo original del día (pasada de cosechadora el 1/10) |
| `backups/2026-10-05-pre-clima-y-siembra.alp` | Ciclo solo cosecha: arranca en `Creciendo` y la máquina cosecha al madurar. Probado: conserva masa |
| `backups/2026-10-05-siembra-v1.alp` | Clima anual + siembra versión 1 (verificado con una corrida) |
| `backups/2026-10-05-pre-visual-lotes.alp` | Igual que el anterior, antes de tocar la animación |
| `backups/2026-10-05-visual-lotes.alp` | Con texto de avance, cuadraditos por lote y trigo según el estado. Sin probar en AnyLogic |
| `backups/2026-10-05-pre-escala-siembra.alp` | Igual que el anterior, antes de cambiar la escala de tiempo de la siembra |
| `backups/2026-10-19-pre-semilla-1a.alp` | Estado mergeado en `main` (PR #2), antes de la semilla |
| `backups/2026-10-19-pre-histeresis-semilla.alp` | Semilla 1a con el bucle infinito (no usar) |
| `backups/2026-10-19-pre-fin-simulation.alp` | Semilla 1a con histéresis y 512 MB, antes de que `Simulation` termine al cerrar la cosecha |

Para volver a un estado anterior, hay que copiar el respaldo sobre `Optimización de la Ventana de Siembra.alp`, con AnyLogic cerrado.

---

## 11. Semilla: la sembradora gasta semilla y el carro la repone (paso 1a, 19/10)

Este cambio es el paso 1a de [PLAN.md](PLAN.md). Antes, la máquina sembraba sin gastar nada. Ahora tiene una tolva de semilla que se vacía mientras siembra, y el carro se la repone desde la cabecera. Si la tolva se queda vacía antes de que llegue el carro, la máquina para.

En esta versión el depósito de la cabecera tiene **stock infinito**: el carro siempre encuentra semilla. El stock finito, repuesto por el camión, era el paso 1b y se descartó.

### La cadena de la semilla

```
depósito (cabecera) ──carro──► tolva de la sembradora ──sembrando──► lote
     stock infinito         entrega de golpe          441 kg/h
```

Es la cadena del grano al revés. El grano sale del lote y termina en el silo. La semilla sale del depósito y termina en el lote.

### Cuánto gasta

`consumo = velocidad × ancho × densidad`. Con 7 km/h (1,944 m/s), 9 m y 70 kg/ha (0,007 kg/m²) da **0,1225 kg/s, o 441 kg/h**. La tolva de 4.000 kg alcanza para unas 9 horas de trabajo.

La semilla se integra igual que el grano, con tres variables en `Combine`: `semilla` (kg en la tolva), `tasaSemilla` (kg por unidad de tiempo, negativa) y `tUltimoSemilla`. La función `actualizarSemilla()` pone el nivel al día con la tasa vigente.

La tasa es **derivada**, igual que la del grano: `tasaSemillaActual()` vale el consumo solo si la máquina está trabajando **y** sembrando. Si no, vale 0. Cada vez que cambia `trabajando` se llama a `actualizarTasaSemilla()`. Eso pasa en cuatro lugares de `Combine`:

| Dónde | Por qué cambia |
|---|---|
| `transition` (llega al lote) | Empieza un lote |
| `transition5` (para) | Para por jornada, piso o falta de semilla |
| `transition8` (reanuda) | Vuelve a trabajar |
| `transition6` (termina el lote) | Termina un lote |

### El statechart `semillaControl` (en `Combine`)

Es un tercer statechart, paralelo a `tankControl` (grano) y `moveControl` (movimiento):

```
            [timeout: hasta el umbral]        [timeout: hasta vaciarse]
Suficiente ─────────── aPedida ──────────► Pedida ──── aAgotada ────► Agotada
    ▲                                         │                         │
    └──────── recuperaPedida [semilla > umbral + 1 kg] ─┘                │
    └──────── recuperaAgotada [semilla > umbral + 1 kg] ────────────────┘
                                   Pedida ◄── recuperaParcial [0 < semilla ≤ umbral + 1 kg] ── Agotada
```

| Estado | Qué significa | Qué hace al entrar |
|---|---|---|
| `Suficiente` | La tolva está por encima del umbral (20% = 800 kg) | Nada |
| `Pedida` | Bajó del umbral y se pidió semilla al carro | Manda `NEED_SEED` al carro |
| `Agotada` | La tolva llegó a 0 | Pone `sinSemilla = true` y la máquina para |

La parada por falta de semilla entra en `puedeTrabajar()`, que sigue siendo el **único punto de parada**: `... && !inState( FullWaitCart ) && !sinSemilla`.

Los timeouts `aPedida` y `aAgotada` se calculan con `tUmbralSemilla()` y `tVaciaSemilla()`: el tiempo que falta para llegar al umbral o a 0 con la tasa actual. Si la máquina está parada, la tasa es 0 y el timeout vale `1e12`, o sea, nunca.

### El carro

El carro tiene tres estados nuevos en `moveControl`:

```
WaitCommand ──[NEED_SEED]──► CargandoSemilla ──[timeout: carga]──► LlevandoSemilla ──[ARRIVED: entrega]──► VolviendoSemilla ──[ARRIVED]──► WaitCommand
                                                                    (se reapunta cada minuto)
```

| Estado | Qué hace |
|---|---|
| `CargandoSemilla` | Llena el carro en la cabecera. El tiempo es lo cargado dividido por `UnloadingRate` (150 kg/s) |
| `LlevandoSemilla` | Viaja hacia la sembradora. Como la sembradora se mueve, se reapunta cada minuto, igual que `GoingToCombine` |
| `VolviendoSemilla` | Vuelve a la cabecera |

Al llegar a la sembradora, el carro vuelca `min( carga del carro, espacio libre en la tolva )` **de golpe**. Es el mismo criterio que el volcado de grano: lo que sale del carro entra a la tolva en el mismo instante, así que conserva por construcción. Después llama a `Combine.semillaEntregada()`, que reprograma los eventos y reevalúa las condiciones.

La carga del carro se guarda en `semillaCarro`, una variable aparte de `nivel`, que es el grano. Así la semilla nunca se mezcla con el grano ni con su auditoría.

### Decisiones (para la defensa)

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Pedir semilla al bajar del 20%, no al vaciarse | Pedir con la tolva vacía | Así trabaja un operario real: llama antes de quedarse sin semilla. El umbral es un parámetro (`umbralSemilla`) |
| Entrega instantánea al llegar | Un flujo continuo carro → tolva | La carga real dura minutos. El flujo continuo exigía fijar las dos tasas y reprogramar dos timeouts, que fue la fuente de casi todos los errores de masa del modelo |
| `WaitCommand` vuelve a mirar si hay un pedido pendiente | Confiar en el mensaje `NEED_SEED` | Si el carro está ocupado cuando llega el mensaje, AnyLogic lo descarta en silencio (aprendizaje 14 del contexto). Es el mismo patrón que ya usaba `WaitCommand` con `GO_TO_COMBINE` |
| Histéresis de 1 kg para salir de `Pedida` y `Agotada` | Comparar contra el umbral exacto | Sin margen se arma un bucle infinito en tiempo cero (ver abajo) |
| Stock infinito en la cabecera (1a) | Modelar el camión desde el principio | Probar la cadena carro → tolva aislada. El 1b, que sumaba el camión, se descartó |

### La trampa del bucle infinito (aprendizaje 23)

La primera versión entraba en un bucle y llenaba la consola con miles de `### PIDE SEMILLA` en el mismo instante. Pasaba esto:

1. `aPedida` dispara cuando la tolva llega a 800 kg.
2. Por redondeo de punto flotante, la semilla queda en 800,0000001 kg, apenas por encima del umbral.
3. `recuperaPedida` (`semilla > 800`) es verdadera y vuelve a `Suficiente`.
4. `aPedida` recalcula su timeout, `(800,0000001 − 800) / tasa ≈ 0`, y vuelve a `Pedida`. Y así sin fin.

El arreglo es pedir `semilla > umbral + 1 kg` para salir. Ese margen solo se supera con una entrega real del carro, de unos 3.200 kg. **Regla:** una condición que deshace lo que hizo un timeout necesita margen.

### Auditoría de semilla

`Main.auditarSemilla()` se llama al terminar la siembra y hace dos comprobaciones independientes:

1. **Conservación:** `semillaDespachada = semillaSembrada + semilla en la tolva + semilla en el carro`. La diferencia es la `FUGA` de semilla, y tiene que ser ruido de punto flotante.
2. **Superficie:** `semillaSembrada` tiene que ser `densidad × superficie realmente recorrida`.

La superficie recorrida **no es 104 ha por lote**. El lote mide 1.300 m de ancho y la máquina hace hileras enteras de 9 m: son 145 hileras, que cubren 1.305 m. Por eso cada lote tiene 104,4 ha. Con la cosecha pasa lo mismo: cada lote da 313,2 t y no 312. La auditoría calcula la superficie a partir de las hileras.

### Parámetros y variables nuevos

| Dónde | Nombre | Valor | Qué es |
|---|---|---|---|
| `Main` (parámetro) | `densidadSiembra` | 70 kg/ha | Semilla por hectárea. **Falta una fuente** (INTA) |
| `Main` (parámetro) | `capacidadSemilla` | 4.000 kg | Tolva de semilla de la sembradora. **Falta una fuente** (ficha técnica) |
| `Main` (parámetro) | `umbralSemilla` | 0,2 | Fracción de la tolva que dispara el pedido |
| `Main` | `semillaDespachada`, `semillaSembrada` | kg | Para la auditoría |
| `Main` | `entregasSemilla`, `horasSinSemilla` | | Para el resultado #2 |
| `Combine` | `semilla`, `tasaSemilla`, `tUltimoSemilla` | | Nivel de la tolva de semilla |
| `Combine` | `sinSemilla`, `tInicioSinSemilla` | | Parada por falta de semilla |
| `Cart` | `semillaCarro`, `ultimaCargaSemilla` | | Semilla que lleva el carro |

La máquina arranca la campaña con la tolva llena. Lo hace el StartupCode de `Main`, y esa carga inicial cuenta como semilla despachada.

### Verificación (campaña 0, 12 lotes, 1 turno)

| Qué | Esperado | Medido |
|---|---|---|
| Consumo | 441 kg/h | 441,0 kg/h (línea `### INICIO LOTE`) |
| Primer pedido | Tras 7,26 h de trabajo | Día 1,286: 6,4 h del día 0 y 0,86 h del día 1 |
| Entregas | 25 a 27, de unos 3.250 kg | 27, de 3.223 a 3.258 kg |
| Horas sin semilla | 0 | 0 |
| `FUGA` de semilla | ~0 | 1,1 × 10⁻¹¹ kg |
| Semilla sembrada | 12 × 104,4 ha × 70 = 87.696 kg | 87.696 kg |
| Fin de siembra | Día 40, igual que sin semilla | Día 40, con 198,86 h, idéntico |

Que la máquina nunca espere semilla confirma la parte 4.2 del plan: con estos valores, la semilla no es un cuello de botella. Importaría si la reposición fuera lenta, pero el stock finito (1b) se descartó: se declara como supuesto.

**Cosecha (campaña 0, 1 lote, 1 turno).** Lo único que este cambio toca de la cosecha es `Cart.WaitCommand`, que ahora distingue siembra de cosecha. Se verificó con una campaña completa de 1 lote:

| Qué | Esperado | Medido |
|---|---|---|
| Entregas de semilla | 2, de unos 3.200 kg | 2, de 3.250 y 3.258 kg |
| Semilla sembrada | 104,4 ha × 70 = 7.308 kg | 7.308 kg, `FUGA` 0 |
| Fin de siembra | | Día 2 (16,6 h de trabajo) |
| Madurez | | Día 130 |
| Horas de cosecha | 21,09 h, igual que antes | 21,09 h |
| Grano cosechado | 313.200 kg | 313.200 kg |
| `FUGA` de grano | ~0 | −1,3 × 10⁻¹¹ kg |
| Viajes de camión | 6 | **5** |

Los 5 viajes no son un error. Antes, la corrida seguía después de cerrar la cosecha y el camión terminaba de llenarse y hacía el sexto viaje. Ahora `Simulation` se detiene al cerrar la cosecha (`terminarAlCerrarCampania`), así que los 63.200 kg que no llegaron al silo quedan en la cosechadora, el carro y el camión. La auditoría los cuenta como masa en el sistema y la `FUGA` da 0. Por la misma razón, con 12 lotes pueden salir 74 viajes en vez de los 75 de antes: depende de cuánto grano quede en la cadena al cerrar.

`viajesCamion` cuenta los viajes que llegaron al silo antes del cierre. Si el entregable #2 necesita los viajes totales, hay que sumar el grano que quedó en la cadena dividido por la capacidad del camión.

### Otros cambios del 19/10

- **Memoria del experimento `Simulation`:** pasó de 64 MB a 512 MB, la misma que el barrido. Con 64 MB el margen era muy chico.
- **`Simulation` termina al cerrar la cosecha** (`terminarAlCerrarCampania = true`). Antes quedaba en `Cosechado` avanzando hasta mayo de 2026 sin nada que hacer.
- **Diagnóstico:** cada lote de siembra imprime `### INICIO LOTE n`, con la semilla en la tolva, la velocidad, el ancho y el consumo.
- **El editor de AnyLogic se trababa, no el modelo.** La herramienta `jstack` viene en la JRE de AnyLogic. Con ella se vio que el modelo seguía corriendo. El IDE, en cambio, recalculaba el panel de propiedades sin parar. Es un problema de SWT sobre Wayland. Mientras corre una simulación, conviene no tener seleccionado un elemento con muchas propiedades.

## 12. Fallas de máquina (paso 2, 19/10)

Este cambio es el paso 2 de [PLAN.md](PLAN.md). Antes, la máquina nunca se rompía, así que todos los tiempos eran un límite optimista. Ahora se rompe mientras trabaja y queda detenida hasta que la reparan. **Verificado con 1 lote (19/10) y con 12 lotes (27/10).**

### El statechart `fallaControl` (en `Combine`)

Es el cuarto statechart paralelo de `Combine`, junto a `tankControl`, `moveControl` y `semillaControl`:

```
Operativa ──[aFalla: timeout]──► Reparando ──[finReparacion: timeout]──► Operativa
```

| Elemento | Qué hace |
|---|---|
| `aFalla` | Timeout en horas: `trabajando ? tHastaFallaHoras() : 1e12`. Solo corre mientras la máquina trabaja |
| `Reparando` (entrada) | Cuenta la falla, pone `reparando = true`, sortea la duración y llama a `moveControl.onChange()` |
| `finReparacion` | Timeout de `duracionReparacion` horas. Pone `reparando = false`, suma las horas y llama a `moveControl.onChange()` |

La falla es un motivo más de parada. Entra en `puedeTrabajar()`, que sigue siendo el único punto de parada: `... && !sinSemilla && !reparando`. No hay mensajes nuevos. El `STOP` lo manda `transition5` al reevaluar la condición, no la transición de falla. Así no se hace `cancel()` sobre una transición que está disparando.

### Cómo se sortea

- **Tiempo hasta la falla:** exponencial de media `mtbfHoras`, medido en **horas de operación**. Una máquina parada no se rompe. `reprogramarFalla()` pone el timeout en `1e12` al parar y vuelve a sortear al reanudar. La exponencial no tiene memoria, así que sortear de nuevo da lo mismo que descontar el tiempo ya trabajado.
- **Duración de la reparación:** `triangular(0,5; 8; 2)` horas (mínimo, máximo, moda), con media de 3,5 h. Corre en tiempo de calendario, no solo en horas de jornada.
- **Generador propio.** Las fallas usan `Combine.rngFalla`, un `java.util.Random` con semilla `Main.semillaFallas`, y no el generador del modelo. Hay dos razones. Agregar fallas no mueve los demás sorteos del modelo, y con `mtbfHoras` muy grande el resultado queda idéntico al de antes. Además, para el barrido del paso 7 alcanza con variar `semillaFallas` para tener réplicas distintas. El experimento usa semilla fija 1, así que sin esto todas las réplicas darían lo mismo.

`reprogramarFalla()` se llama en los cuatro lugares donde cambia `trabajando`, junto a `actualizarTasaSemilla()`: `transition` (empieza el lote), `transition5` (para), `transition6` (termina el lote) y `transition8` (reanuda). Solo actúa si `Operativa` está activo.

### Parámetros y variables nuevos

| Dónde | Nombre | Valor | Qué es |
|---|---|---|---|
| `Main` (parámetro) | `mtbfHoras` | 100 h | Media de horas de operación entre fallas. **Falta una fuente** (ASABE D497.7) |
| `Main` (parámetro) | `semillaFallas` | 1 | Semilla del generador de fallas |
| `Main` | `fallas`, `horasReparando` | | Contadores de la campaña |
| `Main` | `baseFallas`, `baseReparando` | | Foto para que `reportarPasada()` informe solo la pasada |
| `Combine` | `reparando`, `tInicioReparacion`, `duracionReparacion`, `rngFalla` | | Estado de la reparación y generador |

`reportarPasada()` agrega `fallas=N (X h reparando)`. La línea `### MAQUINA PARA` agrega `reparando=`. Cada falla imprime `### FALLA n | dia | repara X h` y cada fin `### REPARADA`.

**`ParametersVariation` ya tiene los parámetros nuevos.** Al guardar el modelo en el IDE (8.9.9, build 202607020720), AnyLogic los agregó solo a `Simulation` y a `ParametersVariation` como `FIXED` (commit `d5ba941`). En el paso 7 hay que pasar `semillaFallas` a variable, no recrear el experimento.

### Cómo verificarlo

Tres corridas de `Simulation`, con `turnos = 1` y `campania = 0`:

| Corrida | Qué se espera |
|---|---|
| 1 lote, `mtbfHoras = 1e9` | **Idéntica a la del 19/10 sin fallas:** siembra el día 2 (16,571 h), madurez el día 130, cosecha el día 134 (21,09 h), 5 viajes, `FUGA` de grano ~1e-11, `FUGA` de semilla 0. No aparece ninguna línea `### FALLA` |
| 1 lote, `mtbfHoras = 5` | Unas 7 fallas (38 h de operación / 5 h). Cada `### FALLA` va seguida de un `### MAQUINA PARA ... reparando=true` en el mismo instante. Ambas `FUGA` siguen en ~0 |
| 12 lotes, `mtbfHoras = 100` | Unas 4,5 fallas (450 h de operación / 100 h) y 16 h en reparación. Siembra más tarde que el día 40 |

Con 1 lote y `mtbfHoras = 100` se espera una falla cada 2 o 3 corridas, así que esa corrida no prueba nada. Por eso la segunda usa 5 h.

### Resultado de las corridas del 19/10

| Corrida | Medido |
|---|---|
| 1 lote, sin fallas | Idéntica a la anterior al dígito: siembra el día 2 (16,571 h), madurez el día 130, cosecha el día 134 (21,09 h), 5 viajes, `FUGA` de grano −1,27e-11. Ninguna línea `### FALLA` |
| 1 lote, `mtbfHoras = 5` | 9 fallas: 2 en la siembra (8,75 h reparando) y 7 en la cosecha (24,34 h). Siembra cierra el día 4, madurez el 132, cosecha el 138. `FUGA` de semilla 3,6e-12 y de grano 1,5e-10 |

- **Las fallas no mueven otros sorteos.** En las dos corridas el cultivo crece 127 días. El generador propio cumple su función.
- **Ninguna falla ocurre con la máquina parada.** Las 9 caen con `jornada=true` y cada `### FALLA` va seguida de `### MAQUINA PARA ... reparando=true` en el mismo instante.
- **Las horas cierran.** Cada duración sorteada coincide con el tiempo entre `### FALLA` y `### REPARADA`, y la suma de cada pasada coincide con el contador `horasReparando`. El trabajo efectivo no cambia (16,571 h y 21,09 h): las fallas solo agregan tiempo detenido.
- **9 fallas con 5 h de MTBF** es compatible con las 7,5 esperadas (38 h de operación / 5 h).
- **Un efecto a tener en cuenta.** Si la máquina se rompe con grano en la tolva y el carro queda libre, el carro va a la máquina parada y se lleva el grano (se ve en la falla 4: la tolva pasa de 1.658 a 0 durante la reparación). Es consecuencia de que `Cart.WaitCommand` atiende cualquier parada de la máquina, no solo la de tolva llena. Conserva masa, pero hay que recordarlo al medir la espera del carro en el paso 4.

### Corrida de 12 lotes del 27/10

Con `cantidadLotes = 12`, `mtbfHoras = 100`, `campania = 0` y `turnos = 1`. Ya incluye la madurez por grados-día (paso 3, sección 13).

| Pasada | Medido |
|---|---|
| Siembra | 4 fallas (días 4, 16, 27 y 35) y 15,65 h reparando. Cierra el **día 42**, dos días después que sin fallas, y sigue dentro de la ventana. Trabajo efectivo 198,857 h, igual que sin fallas. 27 entregas de semilla, `FUGA` de semilla 2,5e-11 |
| Crecimiento | Madura el **día 181** (139 días de ciclo, `gdd` = 1.909,4). Es el día calculado con la serie para una siembra cerrada el día 42 |
| Cosecha | 1 falla (día 199) y 3,93 h reparando. Cierra el día 249. Trabajo 253,09 h, 74 viajes, `FUGA` de grano 6,4e-9 |

- **5 fallas en 452 h de operación**, compatibles con las 4,5 esperadas, con 19,6 h de reparación en total. Una sola corrida no alcanza para medir la media. Eso queda para el barrido del paso 7, variando `semillaFallas`.
- **Ninguna falla ocurre con la máquina parada.** Las cinco van seguidas de `### MAQUINA PARA ... reparando=true` en el mismo instante.
- **Las horas cierran.** En las cinco fallas, el tiempo entre `### FALLA` y `### REPARADA` coincide con la duración sorteada (diferencia menor a 1e-6 h).
- **Una reparación puede terminar fuera de la jornada.** La falla 5 termina a las 15:45, después de la jornada, así que la máquina reanuda al día siguiente. Es lo esperado: la reparación corre en tiempo de calendario. Para el paso 4 conviene saber que, en ese caso, parte del tiempo de reparación coincide con horas no laborables.
- **El efecto se propaga.** Dos días de atraso en la siembra mueven la madurez cuatro días (de 177 a 181) y la cosecha seis (de 243 a 249).

**Qué mirar en el log.** Que ningún `### FALLA` ocurra con la máquina parada (el timeout vale `1e12` en ese caso). Y que después de `### REPARADA` aparezca `### MAQUINA REANUDA` si hay jornada y piso, o que quede parada por esa causa si no.

## 13. Madurez por grados-día (paso 3, 27/10)

Este cambio es el paso 3 de [PLAN.md](PLAN.md). Antes, el período de crecimiento era un sorteo `triangular(90, 150, 120)` días, sin relación con el clima. Ahora el cultivo madura cuando suma una meta de grados-día, calculada con la temperatura real de la campaña. Un año caluroso madura antes y uno fresco, después. **Verificado el 27/10 con 1 y 12 lotes (ver el final de esta sección).**

### Qué cambió

| Elemento (`Main`) | Antes | Ahora |
|---|---|---|
| `Creciendo` (entrada) | Sorteaba `diasHastaMadurez` | Pone `gdd = 0` |
| `transition1` (`Creciendo → Maduro`) | Timeout de `diasHastaMadurez` días | Condición `gdd >= gddObjetivo` |
| `Maduro` (entrada) | | Calcula `diasHastaMadurez = diaMadurez − diaFinSiembra` y lo imprime con `gdd` |
| `gddObjetivo` | 1.680 | **1.900** |

El tick diario ya sumaba `max(0, tmedia − tBase)` a `gdd` mientras `Creciendo` estaba activo, y ya llamaba a `cicloCultivo.onChange()` al final. Por eso la condición se evalúa una vez por día, en el mismo tick que suma los grados-día. El día de madurez es el primer día en que el acumulado llega a la meta.

`diasHastaMadurez` deja de ser un sorteo y pasa a ser una salida: el largo del ciclo medido. Los parámetros `diasMaduracionMin`, `diasMaduracionMax` y `diasMaduracionModa` quedan sin uso. No se borran porque aparecen en la pantalla del experimento `Simulation` y en las listas de los dos experimentos. Se borran en la limpieza del paso 9.

El sorteo eliminado era el único del generador del modelo antes de la cosecha. Con fallas apagadas, la madurez ahora depende **solo** del clima y del día de cierre de la siembra.

### Por qué 1.900

Con las 20 campañas y siembra cerrada el día 40, la meta de 1.680 hacía madurar el cultivo a principios de marzo (mediana del día 156). La de 1.900 da una mediana del día 177 (fin de marzo), más cerca de la cosecha habitual de una soja de noviembre. El cálculo está en la parte 3 de [PLAN.md](PLAN.md). **Falta validar la meta con una fuente** (INTA o Bolsa de Cereales, parte 4.3).

### Limitaciones

- **Sin fotoperíodo.** En la realidad, sembrar tarde acorta el ciclo. Acá lo alarga, porque el cultivo arranca a sumar más tarde. Para siembras hasta fines de noviembre el efecto es chico.
- **Año que no madura.** Si la suma no llega a la meta antes del 30/9, `Creciendo` no sale nunca y `diaMadurez` queda en −1. Con 1.900 y siembra el día 40 no pasa en ninguna de las 20 campañas.

### Cómo verificarlo

Corridas de `Simulation` con `turnos = 1`, `campania = 0` y `mtbfHoras = 1e9` (sin fallas, para que el día de siembra sea el conocido). Los valores esperados salen de la serie embebida en el `.alp`, con la misma cuenta que hace el tick:

| Corrida | Qué se espera |
|---|---|
| 1 lote | Siembra el día 2, como antes. **Madurez el día 147** (145 días de ciclo, `gdd` ≈ 1.902,1) |
| 12 lotes | Siembra el día 40, como antes. **Madurez el día 177** (137 días de ciclo, `gdd` ≈ 1.902,7) |

El `gdd` impreso tiene que ser apenas mayor que 1.900: el excedente es lo que sumó el último día. La siembra no tiene que cambiar, porque el paso 3 solo toca lo que pasa después de `siembraCompleta`. La cosecha sí cambia, porque empieza en otro día. La `FUGA` de grano tiene que seguir en ~0.

Día de madurez esperado por campaña, con siembra cerrada el día 40:

| Campaña | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Día | 177 | 187 | 182 | 169 | 191 | 182 | 169 | 206 | 183 | 186 |

| Campaña | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|
| Día | 177 | 186 | 166 | 201 | 173 | 173 | 164 | 152 | 168 | 166 |

### Resultado de las corridas del 27/10

Las dos corridas usaron `campania = 0`, `turnos = 1` y `mtbfHoras = 1e9`.

| Corrida | Medido |
|---|---|
| 1 lote | Siembra el día 2 (16,571 h, igual que antes). **Madurez el día 147**, 145 días de ciclo, `gdd` = 1.902,1. Cosecha el día 157: 21,09 h de trabajo y 5 viajes, igual que antes. `FUGA` de semilla 0 y de grano 9e-12 |
| 12 lotes | Siembra el día 40 (198,857 h, 27 entregas de semilla, `FUGA` de semilla 1,1e-11, igual que antes). **Madurez el día 177**, 137 días de ciclo, `gdd` = 1.902,7. Cosecha el día 243 (antes, el 236): 253,09 h de trabajo, 74 viajes, `FUGA` de grano 5,9e-9 |

- **El modelo hace la misma cuenta que el cálculo con la serie.** El día de madurez y el `gdd` coinciden al decimal en las dos corridas.
- **La madurez depende del día de siembra.** Sembrar 38 días más tarde atrasa la madurez 30 días, porque el ciclo pasa de 145 a 137 días: el cultivo sembrado más tarde crece con más calor.
- **La siembra no cambió.** El paso 3 solo toca lo que pasa después de `siembraCompleta`.
- **La cosecha cambia de fecha, pero no de horas de trabajo.** La única diferencia es el clima que le toca.
- **74 viajes y no 75.** El grano total es el mismo (3.758.400 kg). La corrida termina cuando la máquina cierra el último lote, no cuando el grano llega al silo: quedan 58.400 kg en el sistema y el viaje 75 no sale. El número de viajes depende del punto del ciclo del camión en que cierra la cosecha. Hay que tenerlo en cuenta al contar viajes en el paso 4.

Respaldo: `backups/2026-10-27-pre-gdd.alp`.

## 14. Causas de parada y horas del carro y del camión (paso 4, 27/10)

Este cambio es el paso 4 de [PLAN.md](PLAN.md) y es la base del resultado #2 (cuellos de botella). Antes, `horasDetenida` mezclaba todas las causas. Ahora cada hora detenida se imputa a una causa, y el carro y el camión informan en qué se les va el tiempo. **Verificado el 27/10 (ver el final de esta sección).**

Los contadores solo miden: no cambian ninguna decisión del modelo. Por eso una corrida con los mismos parámetros tiene que dar exactamente los mismos eventos que antes.

### Causas de parada de la máquina

`Combine.causaActual()` decide la causa. Si coinciden varias, se imputa la de mayor prioridad:

| # | Causa | Cuándo |
|---|---|---|
| 1 | `falla` | `reparando` |
| 2 | `sinSemilla` | `sinSemilla` |
| 3 | `jornada` | Fuera de la jornada (`!main.dentroDeJornada()`) |
| 4 | `sinPiso` | `!main.daPiso` |
| 5 | `esperaCarro` | Tolva llena esperando el carro (`FullWaitCart`) |
| 6 | `traslado` | Viaje del galpón al lote (`GoingToField`). Lo fija ese estado |
| 7 | `otra` | Ninguna de las anteriores. Es un control: tiene que dar 0 h |

**Por qué este orden.** Primero van las causas que paran la máquina pase lo que pase. Una falla de noche se imputa a la falla, porque la reparación corre igual. Una noche de lluvia se imputa a la jornada, porque sin lluvia la máquina tampoco habría trabajado. La espera del carro va última: solo cuenta cuando es lo único que frena a la máquina.

**Cómo se mide.** `registrarCausa()` cierra el tramo de tiempo con la causa vigente y abre otro con la causa de ese momento. Se llama donde puede cambiar una causa:

- al parar y al reanudar (`transition5` y `transition8`);
- al empezar y al terminar un lote (`transition` y `transition6`);
- al terminar una reparación (`finReparacion`) y al recibir semilla con la tolva vacía (salida de `Agotada`);
- en cada tick horario de `Main.tickDiario`, que es donde cambian la jornada y el piso.

Llamarla dos veces en el mismo instante no suma nada.

**Qué cuenta como detenido.** Lo mismo que ya contaba `horasDetenida`: la espera en el lote y el viaje del galpón al lote. La vuelta al galpón y los meses estacionado no cuentan. Por eso la suma de las causas tiene que dar `horasDetenida` de la pasada.

### Horas por estado del carro y del camión

Cada estado llama a `cerrarEstado()` al entrar, y después fija su índice en `estado`:

| Agente | Grupo | Estados |
|---|---|---|
| `Cart` | `ocioso` | `WaitCommand` |
| | `viajando` | `GoingToCombine`, `GoingToUnload`, `LlevandoSemilla`, `VolviendoSemilla` |
| | `conLaMaquina` | `Loading` (al lado de la máquina, trabaje o no) |
| | `esperaCamion` | `WaitTruck` |
| | `descargando` | `Unloading` |
| | `cargaSemilla` | `CargandoSemilla` |
| `Truck` | `esperaCarro` | `WaitCart` |
| | `cargando` | `Loading` |
| | `viajando` | `GoingToBin`, `GoingBack` |
| | `descargando` | `Unloading` (en el silo) |

La siembra se mide desde el inicio de la corrida. La cosecha, desde la madurez: `Maduro` llama a `iniciarPasada()` del carro y del camión, así los meses de crecimiento no cuentan como ocio.

### Elementos nuevos

| Dónde | Nombre | Qué es |
|---|---|---|
| `Main` | `horasParada[8]`, `baseParada[8]` | Horas por causa (índice = número de causa) y foto para informar por pasada |
| `Combine` | `causaParada`, `tCausa`, `enCampo` | Causa vigente, inicio del tramo y si la máquina está en el lote |
| `Combine` | `causaActual()`, `registrarCausa()` | Prioridad de causas y cierre de tramos |
| `Cart`, `Truck` | `horasEstado`, `baseEstado`, `estado`, `tEstado` | Horas por grupo de estados |
| `Cart`, `Truck` | `cerrarEstado()`, `iniciarPasada()`, `reporteEstados()` | Cierre de tramos, inicio de pasada y texto del reporte |

`reportarPasada()` imprime tres líneas nuevas por pasada:

```
SIEMBRA PARADAS | falla=… h sinSemilla=… jornada=… sinPiso=… esperaCarro=… traslado=… otra=… | suma-detenida=…
SIEMBRA CARRO | total=… h | ocioso=… h (…%) | viajando=… | …
SIEMBRA CAMION | total=… h | esperaCarro=… h (…%) | …
```

El CSV del barrido no cambia todavía. Sus columnas se definen en el paso 7, junto con las variables de decisión (parte 4.4 del plan).

### Cómo verificarlo

Una corrida de `Simulation` con los parámetros de la corrida C de la sección 12: `cantidadLotes = 12`, `mtbfHoras = 100`, `campania = 0` y `turnos = 1`.

| Qué | Qué se espera |
|---|---|
| Eventos | **Idénticos a la corrida C**: siembra el día 42, 5 fallas, madurez el día 181, cosecha el día 249, 74 viajes. Los contadores no cambian la dinámica |
| `suma-detenida` | ~0 (ruido de punto flotante) en las dos pasadas |
| `otra` | ~0 |
| `falla` | Igual a las horas de reparación de la pasada: 15,65 h en la siembra y 3,93 h en la cosecha |
| `sinSemilla` | 0, como `horas sin semilla` |
| `esperaCarro` | 0 en la siembra, porque no entra grano. Mayor que 0 en la cosecha |
| `jornada` | La causa más grande. Con 1 turno, unas 17,7 h por día de calendario |
| `total` del carro y del camión | Siembra: la duración de la siembra desde el inicio de la corrida. Cosecha: desde la madurez hasta el cierre |
| Camión en la siembra | 100% `esperaCarro`: no hay grano |

### Resultado de la corrida del 27/10

Con los parámetros de la corrida C: 12 lotes, `mtbfHoras = 100`, `campania = 0` y `turnos = 1`.

**Los eventos son idénticos a la corrida C:** siembra el día 42, 5 fallas, madurez el día 181, cosecha el día 249 y 74 viajes. La `FUGA` de grano (6,4337e-9) coincide al último dígito. Los contadores no cambian la dinámica.

| Pasada | Paradas (horas) | Control |
|---|---|---|
| Siembra (815,68 h detenida) | jornada 768,45 · sinPiso 31,0 · falla 15,65 · traslado 0,57 · sinSemilla 0 · esperaCarro 0 · otra 0 | `suma-detenida` = 1,2e-11 |
| Cosecha (1.386,29 h detenida) | jornada 1.258,36 · sinPiso 102,0 · esperaCarro 21,28 · falla 3,93 · traslado 0,73 · sinSemilla 0 · otra 0 | `suma-detenida` = 6,8e-13 |

| Pasada | Carro | Camión |
|---|---|---|
| Siembra (1.017 h) | ocioso 99,5% · viajando 4,72 h · cargaSemilla 0,19 h | esperaCarro 100% |
| Cosecha (1.643 h) | conLaMaquina 1.251,76 h (76%) · ocioso 310,7 h (19%) · esperaCamion 41,36 h (3%) · viajando 32,31 h · descargando 6,94 h | esperaCarro 1.594,78 h (97%) · viajando 31,08 h · descargando 10,28 h · cargando 6,94 h |

- **Todos los controles cierran.** Las causas suman `horasDetenida`, `otra` da 0, `falla` coincide con las horas de reparación y el `total` del carro y del camión es la duración de la pasada. Lo que el carro descarga coincide con lo que el camión carga (6,94 h).
- **La jornada es la causa dominante.** Es el 91% de lo detenido en la cosecha y el 94% en la siembra. Con 1 turno, la máquina trabaja unas 6 h por día.
- **El piso suma horas enteras** (31 y 102), porque cambia en el tick diario y solo se le imputan las horas de jornada: las demás ya son de `jornada`.
- **La logística pesa poco.** La máquina espera al carro 21,3 h, el 8% de sus 253 h de trabajo. El carro espera al camión 41,4 h. El camión está ocioso el 97% de la cosecha, así que parece sobredimensionado. Es un candidato para comparar tamaños en el barrido (parte 4.4 del plan).
- **En la siembra, el carro de semilla está ocioso el 99,5% del tiempo.** Confirma la parte 4.2 del plan: la semilla no es un cuello de botella.
- **Cuidado al leer `conLaMaquina`.** Incluye las noches en que el carro queda estacionado al lado de la máquina parada. No es tiempo útil.

Respaldo: `backups/2026-10-27-pre-causas-parada.alp`.
