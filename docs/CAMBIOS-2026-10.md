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

Antes, el ciclo volvía de `Maduro` a `SinSembrar` y empezaba otra vuelta. Eso obligaba a reiniciar el contador de días (`diaCampaña = 0`), y ese reinicio hacía que la cosecha leyera el clima de octubre. Con un estado final (`Cosechado`):

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
    diaFinSiembra = diaCampaña;                  // ← respuesta del entregable #1
    traceln( "=== SIEMBRA TERMINADA | ... DENTRO/FUERA de la ventana ..." );
    reportarPasada();
    siembraCompleta = true;
} else {
    diaFinCosecha = diaCampaña;
    traceln( "=== COSECHA TERMINADA | ... dias desde la madurez ..." );
    reportarPasada();
    auditarMasa();                                // conservación del grano
    cosechaCompleta = true;
    if ( terminarAlCerrarCampaña ) { getEngine().finish(); return; }
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
- `resultados.csv` agrega dos columnas: `lotes;turnos;campaña;diaFinSiembra;diaMadurez;diaFinCosecha`.

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
| `Cosechado` | No aplica | La corrida termina al cerrar la cosecha (`terminarAlCerrarCampaña = true` desde el 19/10) |

La siembra usaba `0.05 * day()` y tardaba unos 13 minutos. Se subió a `0.5 * day()` para poder verla completa. Si la cosecha se hace lenta, se sube de la misma forma en el entry de `Maduro`. Se puede cambiar también durante la corrida, con el control de velocidad de la ventana de simulación.

Respaldo previo al cambio visual: `backups/2026-10-05-pre-visual-lotes.alp`. Posterior: `backups/2026-10-05-visual-lotes.alp`.

### Lluvia y piso (27/10)

La animación muestra por qué la máquina no entra al lote. Es solo presentación: no cambia ningún resultado.

| Elemento | Qué muestra |
|---|---|
| `field`, `rectangle`, `rectangle1` y `rectangle2` (campo, parte trabajada e hilera en curso, 2D y 3D) | Sin piso: marrón de barro. Llovió ese día pero da piso: marrón más claro, de tierra mojada (desde el 28/10; antes era gris azulado). Si no, el color original. La parte trabajada y la hilera en curso usan tonos más oscuros que el campo |
| `textSueloPiso` (verde) y `textSueloSinPiso` (rojo), debajo de `textAvance` | La lluvia del día, si da piso, la humedad de la capa superficial y el umbral. Se ve uno u otro según `daPiso` |
| `gotaLluvia3D` (línea replicada, solo 3D) | Las mismas gotas en la vista 3D. Caen en el eje Z (altura), de 120 al suelo: en 3D el eje Y del dibujo es el suelo, así que la línea de 2D quedaría acostada sobre el campo |
| `gotaLluvia` (línea replicada, solo 2D) | Gotas que caen sobre el campo los días de lluvia. Son más cuanta más lluvia hay: `25 + 6 × mm`, hasta 150. Azul oscuro sobre el campo claro o gris, celeste sobre el barro |

- **`Main.lluviaHoy()`** devuelve la lluvia del día en curso, o 0 si el clima todavía no se cargó. Solo lee: la usan las tres figuras.
- **La lluvia es un dato diario.** Las gotas duran todo el día del modelo, porque la serie no dice a qué hora llovió.
- **Las gotas caen con el reloj real, no con el del modelo.** Así se mueven igual con cualquier escala de tiempo. Con la escala de la siembra (medio día por segundo), un día de lluvia se ve unos 2 segundos. El barro dura más, porque la capa superficial tarda días en secarse.
- **Lluvia fuerte = sin piso.** Una lluvia de 5 mm o más (`lluviaBloqueante`) corta el piso ese mismo día. Los días de lluvia con piso son lluvias chicas, sobre el campo marrón claro. Por eso las gotas cambian de color según el fondo: con un solo color celeste no se veían esos días.
- **El color dinámico nunca devuelve `null`:** una figura con relleno `null` queda transparente. Por eso el caso normal repite el color original.

Para verlo, en la campaña 0: el día 22 llueven 22,2 mm y el campo queda sin piso hasta el día 26. Con la escala de la siembra, eso pasa entre los 44 y los 52 segundos de corrida.

Respaldo: `backups/2026-10-27-pre-lluvia-visual.alp`.

### El cultivo crece (27/10, paso 6 del plan)

`crop3D` (una figura por planta, unas 4.000) tenía escala fija 8. Ahora tiene una escala dinámica (`ScaleCode`):

```
8.0 * ( 0.15 + 0.85 * progresoCultivo() )
```

`Main.progresoCultivo()` vale 0 sin sembrar, `gdd / gddObjetivo` mientras crece y 1 desde la madurez. Las plantas aparecen al 15% detrás de la sembradora, crecen con los grados-día y llegan al tamaño completo al madurar. Es solo presentación.

La etiqueta `ScaleCode` de una figura 3D no estaba en este modelo. Se tomó del ejemplo "Agent Based Population Model" que trae AnyLogic, donde un agente crece según su edad. Va después de `ReplicationCode`, como el tamaño dinámico de las figuras replicadas de los ejemplos.

**Verificado el 27/10:** compila (el código generado llama a `shape.setScale(...)`) y la planta crece.

**Color: se resolvió el 28/10 con la opción 1** (ver más abajo, "Color del cultivo en el campo"). Lo que se había averiguado sobre colorear la planta:

- **En 2D no se puede cambiar el color del ícono.** AnyLogic dibuja la figura 3D en 2D como una imagen ya renderizada (`3d_low_poly_wheat.dae_yzx_-6_-5_10_10.png` en la carpeta de compilación).
- **La tabla de colores no admite código.** En los más de 1.000 ejemplos de AnyLogic, `ColorMapping` solo tiene colores fijos.
- **En 3D hay un método, sin garantía.** `Shape3DObject.setColor(String material, Color)` existe, pero la tabla de colores de `crop3D` no guarda nombres de material (el código generado los tiene como `"null"`). El `.dae` tiene `mat_0` y `mat_1`, y no se sabe si `setColor` los reconoce por ese identificador.

Opciones, si se retoma:

1. **El campo cambia de color con el cultivo** (recomendada): verde claro recién sembrado, verde intenso creciendo y amarillo al madurar, con el barro y la lluvia con prioridad. Sirve en 2D y 3D, usa el `FillColorCode` que ya tiene `field` y no agrega figuras.
2. **Círculos en lugar de íconos en 2D**, con radio (`RadiusXCode`) y color dinámicos. Es color en la planta, pero se pierde el dibujo de la espiga y se suman unas 4.000 figuras.
3. **Probar `setColor` en 3D**, recorriendo `crop3D.get( i )` (`ReplicatedShape` tiene `get(int)` y `size()`). Es experimental.

Respaldo: `backups/2026-10-27-pre-crecimiento-visual.alp`.

**Corrección del 28/10: colores del campo.**

- **La hilera en curso no cambiaba de color.** `rectangle1` (la máquina va al norte) y `rectangle2` (va al sur) dibujan la hilera que se está trabajando y tenían color fijo. Con sol no se notaba, porque es el mismo color que la parte trabajada. Con lluvia o barro quedaba como una línea clara sobre el campo. Ahora usan el mismo `FillColorCode` que `rectangle`.
- **La lluvia pone el campo marrón.** Un día con lluvia que da piso pasa de gris azulado a marrón claro: (161, 136, 127) en el campo y (121, 85, 72) en la parte trabajada. El barro sin piso sigue igual. Quedan dos tonos de marrón para que se distinga si la máquina puede entrar.
- **La llovizna no se dibuja.** El marrón y las gotas aparecen con 1 mm o más (`lluviaHoy() >= 1`), el umbral meteorológico de "día de lluvia". Con `> 0`, en octubre y noviembre se veía lluvia el 46% de los días, 14 puntos de ellos por lloviznas de menos de 1 mm. Con el umbral queda en 32%. El texto del indicador sigue mostrando los milímetros reales, y el piso se calcula igual que antes: es solo presentación.
- **Al cambiar de lote**, la parte trabajada vuelve a 0 (`XCompleted = 0` al empezar cada lote) y crece de nuevo, porque el dibujo es un solo lote que se repite. Es intencional: el avance total está en `rectLote`.

Respaldo: `backups/2026-10-28-pre-colores-campo.alp`.

**Color del cultivo en el campo (paso 6, 28/10).** Es la opción 1 de arriba: el color del campo sigue el estado del cultivo, con el barro y la lluvia como prioridad. La lógica está en tres funciones de `Main`, y las figuras solo las llaman (`field` usa `colorCampo()`; `rectangle`, `rectangle1` y `rectangle2` usan `colorTrabajada()`).

| Estado (sin barro ni lluvia) | Campo sin trabajar (`colorCampo`) | Parte trabajada (`colorTrabajada`) |
|---|---|---|
| `SinSembrar` | Amarillo pálido: suelo sin sembrar | Verde claro (197, 225, 165): recién sembrado |
| `Creciendo` | De verde claro a verde intenso (76, 175, 80) según `progresoCultivo()` (`colorCultivo`) | Igual |
| `Maduro` | Ámbar (255, 193, 7): maduro sin cosechar | Ámbar antes de que arranque la cosecha; rastrojo (188, 170, 120) desde el primer lote cosechado |
| `Cosechado` | Rastrojo | Rastrojo |

- **Por qué `Maduro` distingue antes y después de arrancar.** Al terminar la siembra, `XCompleted` queda en el ancho del lote, así que la parte trabajada cubre el campo entero durante el crecimiento. Recién vuelve a 0 cuando empieza el primer lote de cosecha. Hasta entonces (`!combine.enCampo && lotesCompletados == 0`) se pinta del color del cultivo maduro.
- **Barro y lluvia siguen primero**, con los mismos colores de antes.
- Los cuadraditos de `rectLote` no cambian.
- **Detalle visual sin resolver:** en la siembra, con la máquina parada, puede verse una línea clara de una hilera de ancho, a unas 3 hileras del borde de lo sembrado y de toda la altura del campo. Por el ancho parece la hilera en curso (`rectangle1`/`rectangle2`), pero esas figuras usan el mismo `XCompleted` que la parte trabajada y no se encontró la causa. No afecta resultados.

Respaldo: `backups/2026-10-28-pre-color-cultivo.alp`.

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
=== COSECHA TERMINADA | campaña 1 | dia ~200 | ~45 dias desde la madurez
COSECHA | trabajando=~253 h | ... | viajes camion=~75 | ...
AUDITORIA ... FUGA=~0                                    ← el grano se conserva
Campo cosechado el dia ~200 — fin de campaña
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

Los 5 viajes no son un error. Antes, la corrida seguía después de cerrar la cosecha y el camión terminaba de llenarse y hacía el sexto viaje. Ahora `Simulation` se detiene al cerrar la cosecha (`terminarAlCerrarCampaña`), así que los 63.200 kg que no llegaron al silo quedan en la cosechadora, el carro y el camión. La auditoría los cuenta como masa en el sistema y la `FUGA` da 0. Por la misma razón, con 12 lotes pueden salir 74 viajes en vez de los 75 de antes: depende de cuánto grano quede en la cadena al cerrar.

`viajesCamion` cuenta los viajes que llegaron al silo antes del cierre. Si el entregable #2 necesita los viajes totales, hay que sumar el grano que quedó en la cadena dividido por la capacidad del camión.

### Otros cambios del 19/10

- **Memoria del experimento `Simulation`:** pasó de 64 MB a 512 MB, la misma que el barrido. Con 64 MB el margen era muy chico.
- **`Simulation` termina al cerrar la cosecha** (`terminarAlCerrarCampaña = true`). Antes quedaba en `Cosechado` avanzando hasta mayo de 2026 sin nada que hacer.
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

Tres corridas de `Simulation`, con `turnos = 1` y `campaña = 0`:

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

Con `cantidadLotes = 12`, `mtbfHoras = 100`, `campaña = 0` y `turnos = 1`. Ya incluye la madurez por grados-día (paso 3, sección 13).

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

Corridas de `Simulation` con `turnos = 1`, `campaña = 0` y `mtbfHoras = 1e9` (sin fallas, para que el día de siembra sea el conocido). Los valores esperados salen de la serie embebida en el `.alp`, con la misma cuenta que hace el tick:

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

Las dos corridas usaron `campaña = 0`, `turnos = 1` y `mtbfHoras = 1e9`.

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

Una corrida de `Simulation` con los parámetros de la corrida C de la sección 12: `cantidadLotes = 12`, `mtbfHoras = 100`, `campaña = 0` y `turnos = 1`.

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

Con los parámetros de la corrida C: 12 lotes, `mtbfHoras = 100`, `campaña = 0` y `turnos = 1`.

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

## 15. Salidas para el rinde y los costos (paso 5, 28/10)

El paso 5 se divide en dos partes. **El modelo calcula lo físico** (cuándo termina cada lote, cuántas horas trabaja y se detiene la máquina, cuántas fallas tiene) y **el script de análisis calcula la plata** (rinde, costos y margen). Así la sensibilidad a precios, costos y curva de pérdida se recalcula sin volver a simular, y el cálculo de N máquinas (parte 4.1 del plan), que también se hace en el script, usa los mismos datos. Las decisiones de diseño están en el paso 5 de [PLAN.md](PLAN.md).

### Qué cambió en el modelo

| Elemento | Qué hace |
|---|---|
| `Main.diaSiembraLote[]`, `Main.diaCosechaLote[]` | Día (con fracción, día 0 = 1/10) en que termina cada lote. Se llenan en `onCompleted()`, antes de contar el lote |
| `Main.filaPasada()` | Arma 23 columnas con los contadores de la pasada que termina, en el mismo orden que el encabezado del CSV |
| `Main.csvSiembra`, `Main.csvCosecha` | Guardan esa fila. `reportarPasada()` la arma **antes** de que los reportes reinicien las bases. Valen `NA` si la pasada no termina |
| `Main.csvLotes()` | Días por lote separados por `\|`, como `siembra;cosecha`. `NA` para un lote que no terminó |
| `Cart.csvEstados()`, `Truck.csvEstados()` | Horas por estado desde el inicio de la pasada. A diferencia de `reporteEstados()`, no reinicia la pasada |
| `onCompleted()`, al cerrar la cosecha | Imprime `CSV \| ...` con la misma fila, para verificar desde `Simulation` |

### El CSV del barrido

Pasa de 6 a 55 columnas y se escribe en **UTF-8** (el encabezado lleva ñ; el `FileWriter` anterior usaba el encoding de la plataforma y en Windows la rompía).

1. `lotes;turnos;campaña;semillaFallas;diaFinSiembra;diaMadurez;diaFinCosecha`. `semillaFallas` hace falta para comparar escenarios con las mismas semillas.
2. 23 columnas de la siembra con prefijo `s_` y 23 de la cosecha con prefijo `c_`: `trabajando`, `detenida`, `viajes`, `diasSinPiso`, `fallas`, `horasReparando`, las 7 causas de parada (`falla` a `otra`), 6 estados del carro y 4 del camión.
3. `diasSiembraLote;diasCosechaLote`: los días de cada lote separados por `|`.

El encabezado lo arma `BeforeEachExperimentRunCode` con un bucle sobre los nombres por pasada. Si se agrega un contador a `filaPasada()`, hay que agregar su nombre ahí y cambiar el 23 del valor inicial de `csvSiembra` y `csvCosecha`.

### Cómo verificarlo

Con los parámetros de la corrida C de la sección 14 (12 lotes, `mtbfHoras = 100`, `campaña = 0`, `turnos = 1`) los eventos tienen que ser idénticos: siembra el día 42, cosecha el día 249, 74 viajes y la misma `FUGA`. En la línea `CSV |`:

- Las columnas de la siembra coinciden con las líneas `SIEMBRA`, `SIEMBRA PARADAS`, `SIEMBRA CARRO` y `SIEMBRA CAMION`, y las de la cosecha con las de `COSECHA`.
- Hay 46 valores separados por `;` antes de los días por lote.
- Los 12 días de siembra son crecientes y el último coincide con el día de fin de siembra (42). Lo mismo con la cosecha (249).
- No aparece ningún `NA`.

### Resultado de la corrida del 28/10

Corrida de Santiago con AnyLogic **8.9.10**, con los parámetros de la corrida C.

- **La línea `CSV |` es correcta.** Tiene 48 campos (23 + 23 + 2), y sus valores coinciden con los reportes de cada pasada. Las causas suman `detenida` (diferencia de 1e-11 en la siembra y 3e-12 en la cosecha), las horas del carro y del camión suman la duración de la pasada, y los 12 días de siembra (2,45 a 42,39) y de cosecha (188,37 a 251,38) son crecientes. No hay `NA`.
- **La siembra y la madurez son idénticas a la corrida C:** siembra el día 42, 4 fallas y 15,65 h de reparación, las mismas paradas y madurez el día 181.
- **La cosecha difiere.** Cierra el día 251, no el 249: aparece una falla más el día 241 (6 fallas en total, no 5), lo detenido sube de 1.386 a 1.432 h y la espera del carro de 21,3 a 28,3 h. Los viajes siguen en 74 y la `FUGA` es 7,9e-9.

**Se asume que la diferencia viene del cambio de versión de AnyLogic** (8.9.9 en la corrida C, 8.9.10 en esta). Las funciones de fallas no cambiaron, y el código nuevo solo lee contadores. Con `SelectionModeForSimultaneousEvents` en LIFO, un motor que ordene distinto los eventos simultáneos cambia cuántas veces se vuelve a sortear la próxima falla, y desde ahí la secuencia se separa. No se verificó corriendo `main` con 8.9.10.

**Consecuencia para el barrido:** todas las corridas que se comparan tienen que hacerse con la misma versión de AnyLogic. Si no, las mismas semillas no dan las mismas fallas y se pierde la comparación con semillas comunes.

Respaldo: `backups/2026-10-28-pre-rinde-costos.alp`.

## 16. Madurez con distribución triangular (28/10)

Hasta acá la madurez no tenía distribución: el cultivo maduraba al sumar 1.900 grados-día fijos, y con la misma campaña siempre maduraba el mismo día. Ahora **la meta de grados-día se sortea una vez por corrida** y el clima sigue decidiendo qué tan rápido se llega a ella.

```
● ──> SinSembrar ──[siembraCompleta]──> Creciendo ──[gdd >= gddMeta]──> Maduro ──[cosechaCompleta]──> Cosechado
                                         └─ al entrar: gdd = 0
                                                       gddMeta = triangular(gddMinimo, gddMaximo, gddObjetivo)
```

| Elemento | Valor | Qué es |
|---|---|---|
| `gddMinimo` (parámetro nuevo) | 1.700 | Mínimo de la triangular |
| `gddObjetivo` | 1.900 | Ahora es la **moda** de la triangular |
| `gddMaximo` (parámetro nuevo) | 2.100 | Máximo de la triangular |
| `semillaMadurez` (parámetro nuevo) | 1 | Semilla del sorteo, aparte de la de las fallas |
| `gddMeta` (variable nueva) | sorteada | Meta de la corrida. La usan la condición `Creciendo → Maduro` y `progresoCultivo()` |

- **Qué representa.** Que no todos los cultivos necesitan la misma acumulación de calor (variedad, ambiente, densidad). Un año caluroso sigue madurando antes que uno fresco.
- **`Maduro` significa que maduró todo el campo.** Los grados-día se cuentan desde que se cierra la siembra, es decir, desde el último lote sembrado. Los lotes anteriores ya llegaron a la meta. Es conservador: no se puede empezar a cosechar el primer lote hasta que madura el último.
- **Todos los lotes comparten la meta sorteada.** Una meta por lote (cada lote madura por separado) obligaría a tener un estado de cultivo por lote: se descartó por el tamaño del cambio.
- **Los valores 1.700 y 2.100 no tienen fuente.** Son los de la sensibilidad del plan y se declaran como supuesto.
- **Solo mueve la cosecha.** No cambia la siembra (resultado #1) ni el rinde del paso 5, que depende solo de la fecha de siembra.
- **Orden de los argumentos.** `triangular(minimo, maximo, moda, generador)`, el mismo que ya usaba la reparación: `triangular(0.5, 8.0, 2.0)` da reparaciones de hasta 6,7 h, imposible si el 8 fuera la moda.
- **La semilla se mezcla** (`semillaMadurez * 0x9E3779B97F4A7C15L`). `java.util.Random` da casi el mismo primer número con semillas consecutivas: con 1, 2 y 3, el primer `nextDouble()` es 0,7309, 0,7311 y 0,7311. Sin la mezcla, las tres réplicas del barrido sortearían la misma meta.
- **CSV:** dos columnas nuevas después de `semillaFallas`: `semillaMadurez` y `gddMeta` (57 en total). Los parámetros nuevos se agregaron a `Simulation` y a `ParametersVariation`.

**Cómo verificarlo.** Con `semillaMadurez = 1`, la consola dice `madura al sumar N grados-dia` con N entre 1.700 y 2.100, y `Cultivo maduro ... gdd=` muestra una suma apenas mayor que N. Con otra semilla, N cambia y la siembra queda igual.

**Resultado de la corrida del 28/10** (corrida C, `semillaMadurez = 1`, AnyLogic 8.9.10):

- **La meta sorteada es 1.980.** Coincide con la cuenta a mano: el primer número del generador mezclado es 0,822, y la inversa de la triangular da 2.100 − √(0,178 × 400 × 200) = 1.980,7. Eso confirma el orden de los argumentos y la mezcla de la semilla.
- **La siembra es idéntica** (día 42, 4 fallas, mismas paradas y la misma fila `s_` del CSV): el sorteo de la madurez no toca el generador de las fallas.
- **Madura el día 187** (antes 181 con 1.900), con 1.985,5 grados-día y 145 días de ciclo.
- **La cosecha se corre 4 días** y cierra el día 255. Las fallas caen en las mismas horas de trabajo, porque se cuentan en horas de operación: la 5 y la 6 se mueven en el calendario junto con la cosecha. 74 viajes y `FUGA` de 8,2e-9.

**La semilla de las fallas también se mezcla (28/10).** `Combine.generadorFalla()` tenía el mismo problema: con `semillaFallas` 1, 2 y 3, el primer sorteo del tiempo hasta la falla daba 131,3, 131,4 y 131,3 h. El efecto real era chico: `reprogramarFalla()` vuelve a sortear cada vez que la máquina reanuda, así que ese primer sorteo solo cubría el primer tramo de trabajo (unas 6 h, sin falla en ninguna réplica) y los sorteos siguientes ya eran distintos. Se mezcla igual (`semillaFallas * 0x9E3779B97F4A7C15L`; el primer sorteo pasa a 172,6, 47,8 y 251,9 h) para que las réplicas no compartan nada. **Esto cambia las fallas de todas las corridas anteriores**, incluida la corrida C: los resultados de las secciones 12, 14 y 15 quedan como registro, pero ya no se repiten.

**Corrida de verificación del 28/10** (corrida C con las dos semillas mezcladas, `semillaFallas = 1`, `semillaMadurez = 1`):

- **Siembra:** cierra el día 41 (antes 42), con 3 fallas y 6,7 h de reparación (antes 4 y 15,7 h). Las paradas suman lo detenido (1e-11) y la `FUGA` de semilla es 3,6e-11.
- **Madurez:** la meta sigue en 1.980 (no depende de las fallas). Madura el día 186, con 145 días de ciclo.
- **Cosecha:** cierra el día 255, con 1 falla (3,6 h), 74 viajes y `FUGA` de grano de 8,5e-9. La espera del carro es 30,5 h.
- **CSV:** 48 campos en la línea `CSV |`, días por lote crecientes y sin `NA`.

Respaldo: `backups/2026-10-28-pre-madurez-triangular.alp`.

## 17. Réplica y tren: semillas para comparar base contra alternativo (28/10)

El barrido compara el sistema base (12 lotes, 1 tren) contra el alternativo C (18 lotes, 2 trenes de 9). El diseño está en la parte 4.5 de [PLAN.md](PLAN.md). Para que los dos sistemas usen las mismas semillas sin cargarlas a mano, se agregaron dos parámetros a `Main`:

| Elemento | Qué hace |
|---|---|
| `replica` (1 por defecto) | Número de réplica del barrido, de 1 a 5 |
| `tren` (1 por defecto) | Tren del sistema alternativo, 1 o 2. El base usa siempre el 1 |
| `semillaFallasUsada()` | `semillaFallas` si es mayor que 0; si no, `replica + 5 × campaña + 100 × (tren − 1)` (desde el 29/10; antes `replica + 10 × (tren − 1)`). La usa `Combine.generadorFalla()` |
| `semillaMadurezUsada()` | `semillaMadurez` si es mayor que 0; si no, `replica + 5 × campaña` (antes solo `replica`). Los dos trenes comparten la madurez: es el mismo cultivo |

- **`semillaFallas` y `semillaMadurez` pasan a 0 por defecto** (derivar). Con `replica = 1` y `tren = 1` las semillas valen 1, así que `Simulation` repite la corrida de verificación de la sección 16.
- **El tren 1 del alternativo usa las mismas fallas que el base** en cada réplica; el tren 2, otras (semillas 11 a 15).
- **`ParametersVariation`:** `campaña` 0 a 19, `cantidadLotes` 9 y 12, `replica` 1 a 5, `tren` 1 y 2, y `turnos` fijo en 1. Son 400 corridas; las 100 de 12 lotes con `tren = 2` no se usan.
- **CSV:** columnas `replica` y `tren` después de `campaña`, y `semillaFallas`/`semillaMadurez` pasan a ser las semillas usadas (59 columnas).

**Cómo verificarlo.** `Simulation` con los valores por defecto tiene que repetir la sección 16: siembra el día 41 con 3 fallas, meta de 1.980 grados-día, madurez el día 186 y cosecha el día 255. Con `tren = 2` cambian las fallas pero no la meta de madurez.

**Verificado el 29/10** en el IDE (AnyLogic 8.9.10), `Simulation` con los valores por defecto: repite la corrida de la sección 16 al dígito. Siembra el día 41 con 3 fallas (6,69 h), meta de 1.980 grados-día, madurez el día 186, cosecha el día 255 con 1 falla y 74 viajes, `FUGA` de grano 8,5e-9 y de semilla 3,6e-11. La fila `CSV |` es idéntica a la anterior, y los parámetros nuevos aparecen en `Main` con sus etiquetas.

Respaldo: `backups/2026-10-28-pre-sistema-alternativo.alp`.

### Semillas que dependen de la campaña (29/10)

La primera versión derivaba la semilla de la madurez solo de `replica`. Como no dependía de la `campaña`, `gddMeta` tomaba **5 valores en todo el barrido** (los 20 climas de una réplica compartían la misma meta), y la triangular quedaba representada por 5 sorteos. Las fallas tenían el mismo problema: solo 5 secuencias por tren. El TP 2.2 valida cada distribución con miles de valores y el TP 3 pide réplicas independientes, así que se cambió:

| Semilla | Fórmula | Valores distintos en el barrido |
|---|---|---|
| Madurez | `replica + 5 × campaña` | 100 |
| Fallas | `replica + 5 × campaña + 100 × (tren − 1)` | 200 (100 por tren) |

- **Semillas comunes:** el base y el alternativo siguen usando las mismas en cada par (`campaña`, `replica`). El tren 1 del alternativo coincide con el base, y el tren 2 suma 100.
- **Corrida de referencia:** con `campaña = 0`, `replica = 1` y `tren = 1` ambas dan 1, la misma semilla que la corrida verificada. `Simulation` con los valores por defecto tiene que repetir la sección 16 y la verificación del 29/10 (siembra el día 41, meta de 1.980, madurez el día 186, cosecha el día 255).
- **Otras campañas** cambian respecto de antes (con `campaña = 1`, las semillas pasan de 1 a 6).

**Verificado el 29/10** en el IDE (8.9.10): `Simulation` con `campaña = 0`, `replica = 1` y `tren = 1` repite la corrida anterior al dígito (siembra el día 41 con 3 fallas, meta de 1.980, madurez el día 186, cosecha el día 255 con 1 falla y 74 viajes, `FUGA` 8,5e-9) y la fila `CSV |` es idéntica.

Respaldo: `backups/2026-10-29-pre-semillas-campana.alp`.

## 18. Comparación visual de corridas: experimento Compare Runs (29/10)

El barrido (`ParametersVariation`) da la estadística; este experimento sirve para **explicar** una campaña concreta: base y alternativo en pantalla, con el mismo clima y las mismas semillas. Es una ilustración de un año y una réplica, no reemplaza al barrido. Se armó siguiendo el modelo Market (`Models/Market Model`), donde cada corrida termina y su serie de datos se agrega a un gráfico del experimento.

### Qué se agregó al modelo

| Elemento | Qué es |
|---|---|
| `haSembradasDS` | Hectáreas sembradas acumuladas (`Main.haSembradas()`: lotes terminados más la fracción del lote en curso) |
| `haCosechadasDS` | Hectáreas cosechadas acumuladas (`Main.haCosechadas()`: 0 hasta la madurez) |
| `humedadDS` | `humedadSuperficie` [mm] |
| `fallasDS` | `fallas` acumuladas |

Los cuatro son `DataSet` de `Main` con actualización automática cada día, igual que `usersDS` en Market. El eje x queda en la unidad de tiempo del modelo (semanas).

### Cómo se usa: tres corridas con la misma campaña y réplica

| Corrida | `cantidadLotes` | `tren` | Representa |
|---|---|---|---|
| Run 0 | 12 | 1 | Base |
| Run 1 | 9 | 1 | Alternativo, tren 1 |
| Run 2 | 9 | 2 | Alternativo, tren 2 |

El alternativo termina cuando termina el más lento de los dos trenes. Las dos corridas del alternativo se ven como dos curvas, no como una suma.

### El experimento CompareRuns

El experimento **ya está creado en el modelo** (se generó por script copiando la estructura del Compare Runs de Market). Se abre en el proyecto como `CompareRuns`, junto a `Simulation` y `ParametersVariation`: cinco sliders (`campaña`, `replica`, `tren`, `cantidadLotes` y `turnos`) y cuatro gráficos, uno por serie. Lo que sigue describe cómo está armado, por si hay que rehacerlo a mano en el IDE.

**Para usarlo:** correr `CompareRuns`, esperar a que termine la corrida, mover los sliders y volver a correr. Cada corrida agrega una curva a los cuatro gráficos.

### Cómo está armado

1. Recargar el modelo sin guardar. En `Main` tienen que aparecer los cuatro `DataSet`.
2. `New → Experiment → Compare Runs`, como en Market. Variables del experimento (con valor por defecto, y un slider cada una): `campaña` (0 a 19), `replica` (1 a 5), `tren` (1 o 2), `cantidadLotes` (9 a 12) y `turnos` (1 a 3). En `Parameters` se pasan al modelo con el mismo nombre. `terminarAlCerrarCampaña` queda en `true` para que cada corrida termine al cerrar la cosecha.
3. Tiempo: `Stop at specified time`, 52 semanas.
4. En el lienzo del experimento, un gráfico por serie (`chart0` a `chart3`), como el de Market, sin datos propios.
5. `After simulation run` (adaptado del de Market):

```java
parametersOfRuns.add( new Object[] { (double) campaña, (double) replica, (double) tren, (double) cantidadLotes, (double) turnos } );
int n = getEngine().getRunCount();
Color color = spectrumColor( (n * 4) % 21, 21 );
String nombre = "Run " + n + ": " + cantidadLotes + " lotes, tren " + tren + ", campaña " + campaña + ", réplica " + replica;
Plot[] graficos = { chart0, chart1, chart2, chart3 };
DataSet[] series = { root.haSembradasDS, root.haCosechadasDS, root.humedadDS, root.fallasDS };
for ( int i = 0; i < graficos.length; i++ ) {
	while ( graficos[ i ].getCount() >= parametersOfRuns.size() ) graficos[ i ].remove( graficos[ i ].getCount() - 1 );
	graficos[ i ].addDataSet( series[ i ], nombre, color, true, Chart.INTERPOLATION_LINEAR, 1, Chart.POINT_NONE );
}
```

6. Cada slider lleva `ActionCode: variable = (int) value;` y `loadParametersOfRun()` repite el patrón de Market para volver a poner los sliders cuando se elige una serie.

### Para verificar en la primera prueba

- **Eje x en semanas:** la serie de hectáreas sembradas del Run 0 (campaña 0, réplica 1, 12 lotes) tiene que llegar a 1.253 ha cerca de la semana 6 (día 41) y las cosechadas, a 1.253 ha hacia la semana 36 (día 255). Si se prefieren días, se puede convertir con `DataSet.getX(i) * 7` al agregar la serie; no se verificó que `getX` exista en 8.9.10 (la clase base no resuelve con `javap` en este equipo).
- **Velocidad:** el modelo llama a `setRealTimeScale` para ir despacio en la siembra. No se sabe si un Compare Runs la respeta o corre a máxima velocidad.
- El modelo no se probó con los `DataSet` nuevos: se escribieron copiando el patrón de `usersDS` de Market, y hay que abrir el modelo y ver que no marque errores.

### Ritmo de presentación (29/10)

En las primeras corridas de `CompareRuns` la consola mostraba el mismo desarrollo que `Simulation`: siembra, crecimiento, cosecha y fin. Las llamadas a `setRealTimeScale` del statechart `cicloCultivo` (siembra 0,5 días/s, crecimiento 1 semana/s, cosecha 0,05 días/s) son para mirar `Simulation` despacio. `setRealTimeScale` solo guarda la escala, no activa el modo de tiempo real (se verificó con `javap -c`), pero un experimento que corra en tiempo real las respetaría y cada corrida duraría decenas de minutos.

Por eso se agregó el parámetro **`presentacionLenta`** (`true` por defecto):

- Las cuatro llamadas a `setRealTimeScale` son ahora `if ( presentacionLenta ) ...`.
- Con `presentacionLenta = false` el arranque del modelo llama a `getEngine().setRealTimeMode( false )`: tiempo virtual, como en el barrido.
- CompareRuns pasa además `terminarAlCerrarCampaña = false`: la corrida termina por el tiempo de parada (semana 52), como en Market, y no con `getEngine().finish()` llamado desde un evento del modelo. Sospecha (sin confirmar) de que esa llamada dejaba trabada la tercera corrida; si persiste, mirar la consola en busca de excepciones.
- **Bloqueo de la barra tras la 2.ª corrida:** el volcado de hilos de Java mostró el proceso inactivo (sin deadlock) y desde un navegador aparte el experimento siguió corriendo; lo que se traba es la ventana embebida de AnyLogic (Chromium `--app`), que pierde una actualización de estado. Con tiempo virtual puro el motor emite cuadros más rápido de lo que el cliente los consume, por eso `presentacionLenta = false` usa ahora 10 semanas por segundo. Causa **no confirmada**; si la ventana embebida se traba igual, abrir la dirección que imprime la consola en un navegador normal.
- **Consola silenciosa:** el parámetro `trazas` (por defecto `false`; `Simulation` lo pasa en `true`) habilita `Main.traza( texto )`, por donde salen todos los `traceln` de detalle y de resumen. CompareRuns y el barrido quedan sin ruido; los errores (`!!!`, `ERROR!`) siguen saliendo siempre. Apenas se lanza CompareRuns (antes de apretar Play) se imprime `CompareRuns disponible en http://localhost:<puerto>`: la variable del experimento `direccionSesion` se inicializa con `anunciarDireccion()`, que busca en un hilo aparte el puerto que escucha el propio proceso (`netstat`, solo Windows; reintenta hasta 20 s porque el servidor puede arrancar después del experimento). El puerto cambia en cada lanzamiento.
- `CompareRuns` lo pasa en `false`. `Simulation` lo lleva en su lista con el valor por defecto (`true`), así que sigue igual. `ParametersVariation` no lo necesita: ya corre en tiempo virtual.

Respaldo: `backups/2026-10-29-pre-ritmo-compare-runs.alp`.

Respaldos: `backups/2026-10-29-pre-compare-runs.alp` (antes de las series de datos) y `backups/2026-10-29-pre-compare-runs-experimento.alp` (antes del experimento).
