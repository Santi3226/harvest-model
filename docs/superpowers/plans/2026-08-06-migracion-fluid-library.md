# Migración: eliminación de la Fluid Library

**Goal:** Sacar la Fluid Library del modelo para levantar el techo de 5 horas de tiempo simulado que impone AnyLogic PLE, conservando el comportamiento y la animación de los cuatro recipientes (tolva de cosechadora, carro, camión, silo).

**Architecture:** Cada `Tank` se reemplaza por una variable `nivel` (double) con contabilidad por eventos exactos: al entrar a un estado con caudal se registra el instante y la tasa; al salir se integra analíticamente (`nivel += tasa * dt`). Los eventos "lleno" / "vacío" pasan de callbacks del bloque a transiciones **timeout** con el tiempo calculado. La migración es incremental con oráculo: durante las tareas 1-4 la variable convive con el `Tank` original y se compara contra él dentro de la ventana de 5 h; recién cuando coinciden se borran los bloques.

**Estado de ejecución (2026-08-06): Tasks 1 a 7 aplicadas. La Fluid Library ya no está en el modelo.**

Por decisión de priorización se abandonó la estrategia de shadow con oráculo a mitad de camino: el oráculo cumplió su función (detectó que la tasa de transferencia real no es constante, ver más abajo) y se pasó directo al borrado, aceptando volúmenes aproximados. Cambios respecto del plan original:

- **Conversión de unidades:** `UnloadingRate` está declarado como parámetro RATE en `PER_SECOND`, y los `Tank` lo consumían como `KILOGRAM_PER_SECOND`. Todas las tasas se escriben `UnloadingRate / second()` y `harvestRate() / second()` para pasarlas a unidades de tiempo del modelo.
- **Timeouts unidad-independientes:** las transiciones de nivel usan `( ... / tasaActual ) / second()` con unidad **SECOND**, así no se rompen si cambia `ModelTimeUnit`. AnyLogic no expone `infinity()`, se usa el literal `1e12` para desactivar la transición.
- **Cinco transiciones de nivel, no tres:** además de `Cart.Full`, `Cart.trBecameEmpty` y `Combine.Full`, el camión tiene `transition5` ("FULL") y `transition3` ("EMPTY").
- **Reprogramar un timeout no es `restart()`:** ese método no existe en AnyLogic 8.9.9. Verificado con `javap` sobre `com.anylogic.engine.TransitionTimeout`, la API pública es `start()` y `cancel()`; `start()` reevalúa la expresión del timeout y reprograma.
- **Las transiciones de salida de un estado se activan DESPUÉS de su entry action.** Lo confirmó un `RuntimeException: a statechart transition being deactivated is not active` al llamar `cancel()` dentro del entry de `Cart.Loading`. Dos consecuencias:
  1. Cuando un estado se entra "fresco", su timeout ya se evalúa con la tasa que fijó el entry action → **no hace falta reprogramar nada**. Esto vale para `Combine.Full`, `Cart.Full` y `Truck.transition3`.
  2. Solo hay que reprogramar cuando la tasa cambia en un estado **interno** y la transición sale de un compuesto **ancestro** que ya venía activo. Son dos casos: `Cart.trBecameEmpty` (sale de `AtUnloading`, la tasa la fija `Unloading`) y `Truck.transition5` (sale de `AtField`, la tasa la fija `Loading`).
  3. **Nunca reprogramar en un exit action:** la transición puede ser justamente la que está disparando, y `cancel()` sobre una transición que ya se desactivó tira la misma excepción.
- **El silo no hubo que dibujarlo:** Main ya tenía el grupo con el rectángulo `tankBar` y la polilínea `pipe`; solo se reapuntaron a `nivelSilo` / `CapacidadSilo` y a `tasaSilo > 0`.
- **`RequiredLibraryReference`:** el `.alp` declaraba la dependencia `com.anylogic.libraries.fluid` en un bloque aparte de los bloques del diagrama. Borrar los bloques no alcanza; hay que borrar también esa declaración.

**Pendiente conocido:** los volúmenes son aproximados. La transferencia se modela a tasa constante, pero la real está limitada por el abastecimiento aguas arriba (medido: 3.97 kg/s efectivos contra 10 kg/s nominales). Se resuelve con transferencia por lote, diferido a un paso posterior.

**Tech Stack:** AnyLogic 8.9.9 PLE · Statecharts · System Dynamics · Process Modeling Library (única librería sin tope de tiempo) · Java embebido.

## Global Constraints

- PLE limita el tiempo simulado a **5 horas en todas las librerías excepto Process Modeling Library**. El modelo final no debe contener bloques de Fluid, Material Handling ni Pedestrian.
- PLE: máximo **10 tipos de agente** y **200 bloques/poblaciones por tipo de agente**. Hoy hay 4 agentes (Cart, Combine, Main, Truck).
- Archivo objetivo: `/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp`
- No hay repositorio git: cada checkpoint es una **copia con fecha** del `.alp`.
- La integración se hace en **unidades de tiempo del modelo** (`dt = time() - tUltimo`), la misma convención que usa la Fluid Library. Ver "Convención de tasas" más abajo. No usar números de tiempo crudos ni factores de conversión.
- Durante la fase shadow se reutiliza `harvestRate()` **tal cual**, aunque su valor sea físicamente discutible: el objetivo es que el oráculo compare contra el comportamiento real de Fluid. La corrección física se aplica en la Task 7, con `tasaCosechaPorMin()`.

---

## Mapa de elementos afectados

Inventario verificado sobre el `.alp` (los números de línea se mueven al editar; sirven para ubicar, no para parchear a ciegas).

| Agente | Bloque Fluid | Línea | Rol |
|---|---|---|---|
| Combine | `grainIn` (FluidSource) | 2776 | grano que entra del lote |
| Combine | `tank` (Tank) | 2622 | tolva de la cosechadora |
| Combine | `grainOut` (FluidExit) | 2889 | descarga al carro |
| Cart | `grainIn` (FluidEnter) | 1077 | recibe de la cosechadora |
| Cart | `tank` (Tank) | 853 | tolva del carro |
| Cart | `grainOut` (FluidExit) | 1010 | descarga al camión |
| Truck | `grainIn` (FluidEnter) | 6851 | recibe del carro |
| Truck | `tank` (Tank) | 6627 | caja del camión |
| Truck | `grainOut` (FluidExit) | 6784 | descarga al silo |
| Main | `grainIn` (FluidEnter) | 4264 | boca del silo |
| Main | `pipeline` (Pipeline) | 4334 | tránsito hacia el silo — **descartable** |
| Main | `bin` (Tank) | 4117 | silo |

Código acoplado a la librería (4 pares entry/exit):

| Agente | Estado | Entry | Exit |
|---|---|---|---|
| Combine | `Harvesting` | `grainIn.set_rate( harvestRate() )` | `grainIn.set_rate( 0 )` |
| Combine | `WithCart` | `grainOut.connect( main.cart.grainIn )` | `grainOut.disconnect(); send("COMPLETED", main.cart)` |
| Cart | `Unloading` | `grainOut.connect( main.truck.grainIn )` | `grainOut.disconnect()` |
| Truck | `Unloading` | `grainOut.connect( main.grainIn )` | `grainOut.disconnect()` |

Callbacks de nivel a reemplazar por transiciones timeout:
- `Cart.tank`: `onFull` → `send("FULL", this)`, `onEmpty` → `send("EMPTY", this)`
- `Combine.tank`: `onFull` → `send("FULL", this)`

Animaciones (expresiones a reapuntar, un token cada una):
- Cart: `tank.amount() / Capacity * 34` (Width) y `* 20` (ZHeight)
- Combine: `tank.amount() / Capacity * 14` (Width) y `* 10` (ZHeight)
- Truck: `tank.amount() / Capacity * 74` (Width) y `* 25` (ZHeight)
- Silo: usa la animación propia del bloque `bin` → hay que dibujarla (Task 4)

## Patrón canónico

Se aplica idéntico a los cuatro recipientes. Cada agente con recipiente recibe:

- `nivel` (double, inicial 0) — contenido actual
- `tasaActual` (double, inicial 0) — caudal vigente en unidades por unidad de tiempo del modelo (positivo = entra, negativo = sale)
- `tUltimo` (double, inicial 0) — instante de la última integración
- función `actualizarNivel()` — integra y re-ancla el reloj

```java
// actualizarNivel() — void, sin parámetros
double dt = time() - tUltimo;
nivel = max( 0.0, min( Capacity, nivel + tasaActual * dt ) );
tUltimo = time();
```

**Convención de tasas (decidida al implementar Tasks 2-3):** `tasaActual` se expresa en *unidades por unidad de tiempo del modelo*, que es exactamente la convención que usa la Fluid Library para un parámetro de tasa sin unidad. Así el shadow coincide con el `Tank` por construcción, sin factores de conversión y sin importar cuál sea `ModelTimeUnit`. Los parámetros existentes (`UnloadingRate`, `harvestRate()`) se usan **tal cual, sin multiplicar**.

Regla de oro 1: **llamar `actualizarNivel()` antes de cualquier cambio de `tasaActual` y antes de cualquier lectura de `nivel` fuera de la animación.** Si eso se respeta, `nivel` es exacto en todo instante de decisión.

Regla de oro 2: **después de cambiar `tasaActual`, llamar `restart()` en las transiciones de nivel del agente.** AnyLogic evalúa el timeout de una transición al entrar al estado de origen y no lo recalcula solo. Si la tasa cambia sin salir de ese estado — por ejemplo, la cosechadora empieza a descargar en el carro sin dejar de cosechar — el evento "lleno" quedaría agendado con la tasa vieja. `restart()` lo reagenda con el valor nuevo.

Tiempos de evento:
- hasta llenarse: `( Capacity - nivel ) / tasaActual` (en unidades de tiempo del modelo)
- hasta vaciarse: `nivel / -tasaActual` (en unidades de tiempo del modelo)

En el desplegable de unidad de la transición hay que elegir la **misma unidad que `ModelTimeUnit`** (minutos, tras la Task 0).

---

### Task 0: Baseline y checkpoint inicial

**Files:**
- Copiar: `Optimización de la Ventana de Siembra.alp` → `backups/`
- Modify: propiedades del modelo (nodo raíz del árbol de Projects)

**Interfaces:**
- Produces: copia de respaldo verificable; `ModelTimeUnit = Minute` para el resto del plan.

- [ ] **Step 1: Cerrar AnyLogic y respaldar**

```bash
mkdir -p "/home/renaiss/Models/Harvest Simulator/backups" && cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-pre-migracion.alp"
```

- [ ] **Step 2: Verificar que el respaldo es idéntico**

```bash
diff "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-pre-migracion.alp" && echo "respaldo OK"
```

Esperado: `respaldo OK`, sin diferencias.

- [ ] **Step 3: Fijar la unidad de tiempo del modelo en Minute**

Abrir AnyLogic → seleccionar el nodo raíz del modelo en el árbol de Projects → Properties → **Model time units: minutes**.

Motivo: las fórmulas del plan están en minutos y la unidad `Week` actual ya causó un bug silencioso en `harvestRate()`. El idioma `/ minute()` protege igual, pero conviene no acumular deuda.

- [ ] **Step 4: Correr el baseline y anotar los valores de referencia**

Properties del experimento `Simulation` → Model time → **Stop at specified time = 240 minutes** (4 h, dentro del techo de PLE). Ejecutar con control automático tildado.

Anotar al final de la corrida: `combine.tank.amount()`, `cart.tank.amount()`, `truck.tank.amount()`, `bin.amount()`. Estos son los números contra los que se valida toda la migración.

- [ ] **Step 5: Checkpoint**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task0-baseline.alp"
```

---

### Task 1: Tolva de la cosechadora en paralelo (shadow) + oráculo

Es la tarea que valida el patrón. Si esta cierra, las tres siguientes son mecánicas.

**Files:**
- Modify: agente `Combine` — variables nuevas, función nueva, entry/exit de `Harvesting` y `WithCart`
- Modify: agente `Main` — evento de comparación

**Interfaces:**
- Produces: `Combine.nivel`, `Combine.tasaActual`, `Combine.tUltimo`, `Combine.actualizarNivel()`, `Combine.tasaCosechaPorMin()`

- [ ] **Step 1: Crear las variables en Combine**

Abrir el agente `Combine`. Desde la paleta **Agent**, arrastrar tres elementos **Variable** al diagrama y configurarlos:

| Name | Type | Initial value |
|---|---|---|
| `nivel` | double | `0` |
| `tasaActual` | double | `0` |
| `tUltimo` | double | `0` |

- [ ] **Step 2: Crear la función `actualizarNivel()` en Combine**

Paleta **Agent** → **Function**. Name: `actualizarNivel`. Returns: `void` (Just action). Body:

```java
double dtMin = ( time() - tUltimo ) / minute();
nivel = max( 0, min( Capacity, nivel + tasaActual * dtMin ) );
tUltimo = time();
```

- [ ] **Step 3: Crear la función `tasaCosechaPorMin()` en Combine**

Paleta **Agent** → **Function**. Name: `tasaCosechaPorMin`. Returns: `double`. Body:

```java
// reemplazo fisicamente correcto de harvestRate(), en unidades por minuto
return getSpeed( MPS ) * scale.toLengthUnits( RowWidth, METER ) * HarvestDensity * 60;
```

**No usar esta función todavía.** Durante la fase shadow (Tasks 1-6) el objetivo es *imitar* a Fluid, bugs de unidad incluidos, para que el oráculo pueda comparar. Por eso las acciones de abajo usan `harvestRate()`. El cambio a `tasaCosechaPorMin()` se hace en la Task 7, cuando Fluid ya no está y el modelo debe ser correcto.

- [ ] **Step 4: Enganchar la carga en el estado `Harvesting`**

Seleccionar el estado compuesto `Harvesting`. **Entry action**, agregar debajo de la línea existente:

```java
grainIn.set_rate( harvestRate() );
actualizarNivel();
tasaActual = harvestRate();
tUltimo = time();
```

**Exit action**, agregar debajo de la línea existente:

```java
grainIn.set_rate( 0 );
actualizarNivel();
tasaActual = 0;
```

- [ ] **Step 5: Enganchar la descarga en el estado `WithCart`**

Seleccionar el estado `WithCart`. **Entry action**:

```java
grainOut.connect( main.cart.grainIn );
actualizarNivel();
tasaActual = harvestRate() - UnloadingRate;
tUltimo = time();
```

**Exit action**:

```java
grainOut.disconnect();
send( "COMPLETED", main.cart );
actualizarNivel();
tasaActual = harvestRate();
```

Nota: mientras descarga al carro la cosechadora **sigue cosechando**, por eso la tasa neta es la resta. Si el estado `WithCart` puede activarse con la máquina detenida, `tasaCosechaPorMin()` devuelve 0 por sí solo (velocidad 0) y la fórmula sigue siendo correcta.

- [ ] **Step 6: Crear el oráculo de comparación en Main**

Abrir `Main`. Paleta **Agent** → **Event**. Name: `chequeoMigracion`. Trigger type: **Timeout**, Mode: **Cyclic**, Recurrence: `1` minutes. Action:

```java
double dif = abs( combine.nivel - combine.tank.amount() );
if ( dif > 0.01 ) {
    traceln( "DESVIO combine @" + time( MINUTE ) + " min | nivel=" + combine.nivel
             + " tank=" + combine.tank.amount() + " dif=" + dif );
}
```

- [ ] **Step 7: Correr y verificar que el shadow coincide**

Ejecutar con Stop time = 240 minutes y control automático tildado.

Esperado: **ninguna línea `DESVIO combine`** en la consola. Si aparecen desvíos, el error está en algún camino de entrada/salida del estado que no llama a `actualizarNivel()` antes de tocar `tasaActual` — revisar todas las transiciones que entran o salen de `Harvesting` y `WithCart`.

- [ ] **Step 8: Checkpoint**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task1-combine-shadow.alp"
```

---

### Task 2: Tolva del carro en paralelo

**Files:**
- Modify: agente `Cart` — variables, función, entry/exit de `Loading` y `Unloading`
- Modify: agente `Main` — ampliar `chequeoMigracion`

**Interfaces:**
- Consumes: `Combine.actualizarNivel()` (patrón)
- Produces: `Cart.nivel`, `Cart.tasaActual`, `Cart.tUltimo`, `Cart.actualizarNivel()`

- [ ] **Step 1: Crear las variables en Cart**

Abrir el agente `Cart`. Tres elementos **Variable**:

| Name | Type | Initial value |
|---|---|---|
| `nivel` | double | `0` |
| `tasaActual` | double | `0` |
| `tUltimo` | double | `0` |

- [ ] **Step 2: Crear `actualizarNivel()` en Cart**

**Function**, Name `actualizarNivel`, returns `void`, body:

```java
double dtMin = ( time() - tUltimo ) / minute();
nivel = max( 0, min( Capacity, nivel + tasaActual * dtMin ) );
tUltimo = time();
```

- [ ] **Step 3: Enganchar la carga en el estado `Loading`**

Seleccionar el estado `Loading` de `Cart`. **Entry action**:

```java
actualizarNivel();
tasaActual = main.combine.UnloadingRate;
tUltimo = time();
```

**Exit action**:

```java
actualizarNivel();
tasaActual = 0;
```

- [ ] **Step 4: Enganchar la descarga en el estado `Unloading`**

Seleccionar el estado `Unloading` de `Cart`. **Entry action**, debajo de la línea existente:

```java
grainOut.connect( main.truck.grainIn );
actualizarNivel();
tasaActual = -UnloadingRate;
tUltimo = time();
```

**Exit action**, debajo de la existente:

```java
grainOut.disconnect();
actualizarNivel();
tasaActual = 0;
```

- [ ] **Step 5: Ampliar el oráculo en Main**

Editar la acción del evento `chequeoMigracion`, agregando:

```java
double difCart = abs( cart.nivel - cart.tank.amount() );
if ( difCart > 0.01 ) {
    traceln( "DESVIO cart @" + time( MINUTE ) + " min | nivel=" + cart.nivel
             + " tank=" + cart.tank.amount() + " dif=" + difCart );
}
```

- [ ] **Step 6: Correr y verificar**

Stop time 240 minutes, control automático tildado.

Esperado: sin líneas `DESVIO combine` ni `DESVIO cart`.

- [ ] **Step 7: Checkpoint**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task2-cart-shadow.alp"
```

---

### Task 3: Caja del camión en paralelo

**Files:**
- Modify: agente `Truck` — variables, función, entry/exit de `Loading` y `Unloading`
- Modify: agente `Main` — ampliar `chequeoMigracion`

**Interfaces:**
- Produces: `Truck.nivel`, `Truck.tasaActual`, `Truck.tUltimo`, `Truck.actualizarNivel()`

- [ ] **Step 1: Crear las variables en Truck**

| Name | Type | Initial value |
|---|---|---|
| `nivel` | double | `0` |
| `tasaActual` | double | `0` |
| `tUltimo` | double | `0` |

- [ ] **Step 2: Crear `actualizarNivel()` en Truck**

**Function**, Name `actualizarNivel`, returns `void`, body:

```java
double dtMin = ( time() - tUltimo ) / minute();
nivel = max( 0, min( Capacity, nivel + tasaActual * dtMin ) );
tUltimo = time();
```

- [ ] **Step 3: Enganchar la carga en el estado `Loading`**

Estado `Loading` de `Truck`. **Entry action**:

```java
actualizarNivel();
tasaActual = main.cart.UnloadingRate;
tUltimo = time();
```

**Exit action**:

```java
actualizarNivel();
tasaActual = 0;
```

- [ ] **Step 4: Enganchar la descarga en el estado `Unloading`**

Estado `Unloading` de `Truck`. **Entry action**, debajo de la existente:

```java
grainOut.connect( main.grainIn );
actualizarNivel();
tasaActual = -UnloadingRate;
tUltimo = time();
```

**Exit action**, debajo de la existente:

```java
grainOut.disconnect();
actualizarNivel();
tasaActual = 0;
```

- [ ] **Step 5: Ampliar el oráculo en Main**

Agregar a la acción de `chequeoMigracion`:

```java
double difTruck = abs( truck.nivel - truck.tank.amount() );
if ( difTruck > 0.01 ) {
    traceln( "DESVIO truck @" + time( MINUTE ) + " min | nivel=" + truck.nivel
             + " tank=" + truck.tank.amount() + " dif=" + difTruck );
}
```

- [ ] **Step 6: Correr y verificar**

Stop time 240 minutes, control automático tildado. Esperado: sin líneas `DESVIO`.

- [ ] **Step 7: Checkpoint**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task3-truck-shadow.alp"
```

---

### Task 4: Silo en paralelo

El silo solo acumula: no tiene salida ni se vacía. Es el recipiente más simple y **no hay motivo para dejarlo fuera de la migración**.

**Files:**
- Modify: agente `Main` — variables, función, ampliar `chequeoMigracion`
- Modify: agente `Truck` — sumar el aporte al silo

**Interfaces:**
- Produces: `Main.nivelSilo`, `Main.tasaSilo`, `Main.tUltimoSilo`, `Main.actualizarSilo()`

- [ ] **Step 1: Crear las variables en Main**

| Name | Type | Initial value |
|---|---|---|
| `nivelSilo` | double | `0` |
| `tasaSilo` | double | `0` |
| `tUltimoSilo` | double | `0` |

- [ ] **Step 2: Crear `actualizarSilo()` en Main**

**Function**, Name `actualizarSilo`, returns `void`, body:

```java
double dt = time() - tUltimoSilo;
nivelSilo = max( 0.0, nivelSilo + tasaSilo * dt );
tUltimoSilo = time();
```

Sin tope superior a propósito: el silo del modelo no debe rebalsar; si querés modelar capacidad finita, agregá el parámetro y usá `min( CapacidadSilo, ... )`.

- [ ] **Step 3: Alimentar el silo desde la descarga del camión**

Volver al estado `Unloading` de `Truck` y dejar las acciones así (reemplazan a las de Task 3, Step 4):

**Entry action**:

```java
grainOut.connect( main.grainIn );
actualizarNivel();
tasaActual = -UnloadingRate;
tUltimo = time();
main.actualizarSilo();
main.tasaSilo = UnloadingRate;
main.tUltimoSilo = time();
```

**Exit action**:

```java
grainOut.disconnect();
actualizarNivel();
tasaActual = 0;
main.actualizarSilo();
main.tasaSilo = 0;
```

- [ ] **Step 4: Ampliar el oráculo en Main**

Agregar a la acción de `chequeoMigracion`:

```java
double difSilo = abs( nivelSilo - bin.amount() );
if ( difSilo > 0.01 ) {
    traceln( "DESVIO silo @" + time( MINUTE ) + " min | nivel=" + nivelSilo
             + " bin=" + bin.amount() + " dif=" + difSilo );
}
```

- [ ] **Step 5: Correr y verificar**

Stop time 240 minutes, control automático tildado.

Esperado: sin líneas `DESVIO`. Si el silo desvía y los otros tres no, la causa es el `pipeline`: introduce un retardo de tránsito que la variable no reproduce. Ver el anexo de descartables.

- [ ] **Step 6: Checkpoint**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task4-silo-shadow.alp"
```

---

### Task 5: Pasar el control a las variables

Hasta acá las variables solo observaban. Ahora toman el mando: los disparos por "lleno"/"vacío" dejan de venir de los callbacks del `Tank`.

**Files:**
- Modify: agente `Combine` — transición `Full`
- Modify: agente `Cart` — transiciones `Full` y `trBecameEmpty`

**Interfaces:**
- Consumes: `nivel`, `tasaActual` de Tasks 1-3

- [ ] **Step 1: Convertir la transición `Full` de Combine**

Seleccionar la transición `Full` en el statechart de `Combine`. Cambiar **Triggered by** de `Message` a **Timeout**, y en Timeout poner (unidad: **minutes**):

```java
tasaActual > 0 ? ( Capacity - nivel ) / tasaActual : infinity()
```

`infinity()` desactiva la transición mientras no haya carga, que es exactamente lo que hacía el callback al no dispararse nunca.

- [ ] **Step 2: Convertir la transición `Full` de Cart**

Misma operación en el statechart de `Cart`, transición `Full`. **Triggered by: Timeout**, valor (unidad **minutes**):

```java
tasaActual > 0 ? ( Capacity - nivel ) / tasaActual : infinity()
```

- [ ] **Step 3: Convertir la transición `trBecameEmpty` de Cart**

Transición `trBecameEmpty`. **Triggered by: Timeout**, valor (unidad **minutes**):

```java
tasaActual < 0 ? nivel / -tasaActual : infinity()
```

- [ ] **Step 4: Reagendar los timeouts cuando cambia la tasa**

Sin esto, el evento "lleno" de la cosechadora queda agendado con la tasa que había al entrar a `Harvesting` e ignora el cambio que produce la descarga al carro.

En `Combine`, agregar `Full.restart();` como **última línea** de las cuatro acciones tocadas en Task 1:
- entry de `Harvesting`, exit de `Harvesting`, entry de `WithCart`, exit de `WithCart`

En `Cart`, agregar estas dos líneas como **últimas** de las cuatro acciones tocadas en Task 2:

```java
Full.restart();
trBecameEmpty.restart();
```

- entry de `Loading`, exit de `Loading`, entry de `Unloading`, exit de `Unloading`

`Truck` no tiene transiciones disparadas por nivel, así que no lleva `restart()`.

- [ ] **Step 5: Correr y comparar contra el baseline**

Stop time 240 minutes, control automático tildado.

Esperado: sin líneas `DESVIO`, y los cuatro valores finales dentro del 1% de los anotados en Task 0 Step 4. Un desvío mayor significa que el timeout se está evaluando con un `nivel` desactualizado: revisar que el estado de origen llame a `actualizarNivel()` en su entry antes de que la transición se arme, y que no falte ningún `restart()`.

- [ ] **Step 6: Checkpoint**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task5-control-variables.alp"
```

---

### Task 6: Animaciones sobre las variables

**Files:**
- Modify: animaciones `tankBar` de `Cart`, `Combine`, `Truck`
- Modify: agente `Main` — figura nueva para el silo

**Interfaces:**
- Consumes: `nivel` de Tasks 1-3, `nivelSilo` de Task 4

- [ ] **Step 1: Reapuntar la barra del carro**

En `Cart`, seleccionar la figura `tankBar`. En Dynamic Properties reemplazar:

- Width: `nivel / Capacity * 34`
- Z-Height: `nivel / Capacity * 20`

- [ ] **Step 2: Reapuntar la barra de la cosechadora**

En `Combine`, figura `tankBar`:

- Width: `nivel / Capacity * 14`
- Z-Height: `nivel / Capacity * 10`

- [ ] **Step 3: Reapuntar la barra del camión**

En `Truck`, figura `tankBar`:

- Width: `nivel / Capacity * 74`
- Z-Height: `nivel / Capacity * 25`

- [ ] **Step 4: Dibujar el silo**

El bloque `bin` aportaba su propia animación, así que hay que reemplazarla. En `Main`, sobre la posición actual del silo: dibujar un **rectángulo** de contorno (el tanque) y adentro otro rectángulo relleno como nivel. Al rectángulo de nivel, en Dynamic Properties:

- Height: `nivelSilo / CapacidadSiloVisual * 60`

Crear antes el parámetro `CapacidadSiloVisual` (double, default `10000`) en `Main` — es solo la escala del dibujo, no un límite físico.

- [ ] **Step 5: Correr y verificar visualmente**

Stop time 240 minutes. Las tres barras deben moverse igual que antes de la migración y el silo debe subir de forma monótona.

- [ ] **Step 6: Checkpoint**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task6-animaciones.alp"
```

---

### Task 7: Borrar la Fluid Library y levantar el techo

**Files:**
- Modify: agentes `Combine`, `Cart`, `Truck`, `Main` — eliminar bloques
- Modify: experimento `Simulation` — stop time
- Modify: agente `Main` — retirar el oráculo

**Interfaces:**
- Consumes: todo lo anterior

- [ ] **Step 1: Quitar las llamadas a la API de Fluid**

Borrar estas líneas (y solo estas) de las acciones donde fueron agregadas:

- `Combine` / `Harvesting`: `grainIn.set_rate( harvestRate() );` y `grainIn.set_rate( 0 );`
- `Combine` / `WithCart`: `grainOut.connect( main.cart.grainIn );` y `grainOut.disconnect();`
- `Cart` / `Unloading`: `grainOut.connect( main.truck.grainIn );` y `grainOut.disconnect();`
- `Truck` / `Unloading`: `grainOut.connect( main.grainIn );` y `grainOut.disconnect();`

Conservar `send( "COMPLETED", main.cart );` en el exit de `WithCart`: es mensajería de statechart, no de Fluid.

- [ ] **Step 2: Borrar los bloques**

Eliminar del diagrama de cada agente:

- `Combine`: `tank`, `grainIn`, `grainOut`
- `Cart`: `tank`, `grainIn`, `grainOut`
- `Truck`: `tank`, `grainIn`, `grainOut`
- `Main`: `bin`, `grainIn`, `pipeline`

Borrar también la función `harvestRate()` de `Combine`, ya reemplazada por `tasaCosechaPorMin()`.

- [ ] **Step 3: Retirar el oráculo**

Borrar el evento `chequeoMigracion` de `Main`. Ya no hay `Tank` contra el cual comparar y el modelo no compilaría.

- [ ] **Step 4: Verificar que no quedan referencias**

Cerrar AnyLogic y correr:

```bash
grep -c 'libraries.fluid' "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp"
```

Esperado: `0`. Cualquier otro número indica un bloque o una referencia de parámetro sin borrar.

- [ ] **Step 5: Levantar el horizonte más allá del techo de PLE**

Abrir AnyLogic → Properties del experimento `Simulation` → Model time → **Stop at specified time**, valor equivalente a 30 días: `43200` minutes.

- [ ] **Step 6: La prueba decisiva**

Ejecutar.

Esperado: la corrida **pasa de los 300 minutos sin el mensaje de la Fluid Library** y llega a 43200. Este es el criterio de éxito de todo el plan.

- [ ] **Step 7: Checkpoint final**

```bash
cp "/home/renaiss/Models/Harvest Simulator/Optimización de la Ventana de Siembra.alp" "/home/renaiss/Models/Harvest Simulator/backups/2026-08-06-task7-sin-fluid.alp"
```

---

## Anexo: qué queda fuera de alcance

Aplicando tu criterio de descartar lo que sea desproporcionadamente complejo:

**`pipeline` (Main) — se descarta, no se reemplaza.** Es el único elemento cuyo comportamiento exacto (grano en tránsito ocupando un ducto con retardo espacial) requiere maquinaria propia para reproducirse. Su efecto es un retardo entre que el camión descarga y que el silo acumula. Es cosmético: no cambia el total transportado ni ningún KPI del TP. Con la migración, la descarga al silo pasa a ser directa. Si en algún momento hiciera falta el retardo, se resuelve con un bloque `Delay` de la Process Modeling Library, que no tiene tope de tiempo.

**Lo que NO se descarta, contra lo que podía suponerse:** el silo. Es un acumulador puro (`nivelSilo += ...`), la pieza más simple del conjunto, y sostiene el total cosechado que después alimenta el análisis financiero del TP. Sacarlo costaría más de lo que ahorra.

## Fase de integridad (posterior al borrado)

Invariante de conservación instalado en `Main.auditarMasa()`, llamado desde `onCompleted()`:

```
totalCosechado == combine.nivel + cart.nivel + truck.nivel + nivelSilo + masaDescartada − masaInventada
```

`masaDescartada` y `masaInventada` contabilizan lo que antes desaparecía en el `max(0, min(Capacity, ...))`. El recorte dejó de ser silencioso.

Defectos detectados y su estado:

- **Cosechaba estando parada (corregido).** La transición `Full` manda `STOP` y la máquina se detiene, pero la tasa seguía activa y el nivel se comía contra el tope. `FullWaitCart` ahora pone `tasaCosecha` y `tasaActual` en cero.
- **Eslabón roto `START_LOADING` (corregido).** Con Fluid, el tanque del camión se llenaba por la conexión de puertos **sin importar el estado de su statechart**: `Loading` era decorativo. Al pasar a variables, el nivel solo crece dentro de `Loading`, y nadie emitía `START_LOADING`, así que el camión nunca cargaba, el silo quedaba vacío y el carro descargaba al vacío (fuga medida: 170%). Lo emite `Cart.Unloading` al entrar. **Lección general: todo acoplamiento que Fluid resolvía por conexión de puertos hay que reponerlo como mensaje explícito.**
- **Timeouts obsoletos tras interrupción (corregido).** Se reprograman en las transiciones de retorno (`Truck.transition1`, `Cart.trTruckDeparted`), no en los exit actions, donde `cancel()` puede caer sobre la transición que está disparando.
- **Transferencias sin conservación (pendiente).** Origen y destino usan la misma tasa nominal, pero ninguno mira el estado del otro: si el origen se vacía, sigue "entregando" y el destino sigue recibiendo. Se resuelve con transferencia por lote.

Verificación de cableado de mensajes (vale la pena repetirla ante cualquier cambio): cruzar los `send( "X", ... )` contra los `EqualsExpression` de las transiciones **que sigan teniendo `Trigger="message"`**. Los campos de los otros triggers quedan en el XML y dan falsos positivos.

## Fuera de este plan

Estas piezas del TP dependen de que la migración esté hecha, pero no forman parte de ella:

- Campaña de siembra (sembradora + reposición de insumos) reusando el mismo patrón de recipientes
- Submodelo de System Dynamics de humedad de suelo y la variable de control "da piso"
- Fallas mecánicas y colas logísticas con Process Modeling Library
- Acople `rindeEfectivo = rindePotencial * penalizacionPorFecha( fechaSiembra )`
- Experimento Monte Carlo para las curvas de probabilidad
