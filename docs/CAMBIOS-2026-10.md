# Cambios de octubre 2026: ciclo completo de campaña y clima anual

Este documento explica qué cambió en el modelo el 5 de octubre de 2026, cómo funciona ahora y por qué se decidió así. Está pensado para que cualquiera del grupo pueda leerlo, entender el código y defender las decisiones frente al docente.

No hace falta haber seguido la conversación en la que se hicieron los cambios. Sí conviene conocer lo básico de AnyLogic (agente, statechart, estado, transición). Esos términos están explicados en la Parte 2 de [ventana-siembra.html](ventana-siembra.html).

**Estado:** la siembra sin reabastecimiento de semilla (versión 1) y el clima anual están implementados y **verificados con una corrida de `Simulation`** (sección 8). El reabastecimiento de semilla (versión 2) es el paso siguiente.

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
| `Cosechado` | `1 * week()` | Sin nada que mirar |

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
- **Reabastecimiento de semilla (versión 2):** la sembradora gasta semilla, y cuando le queda poca llama al carro, que se la lleva desde la cabecera. Si se queda vacía antes de que llegue, se para. El tiempo parado esperando semilla es un dato directo para el entregable #2 (cuellos de botella).
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

Para volver a un estado anterior, hay que copiar el respaldo sobre `Optimización de la Ventana de Siembra.alp`, con AnyLogic cerrado.
