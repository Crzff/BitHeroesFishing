# Presupuesto de farmeo — componente offline

Contrato del 2026-10-02. Complementa `SPEC-dungeon-runner.md`; **no cambia su
política sin compras ni conecta nuevas acciones al juego**. Implementación en
`fishing_core/farm_budget.py`, sin dependencias adicionales.

## Primera entrega: energía, intentos y tiempo

- `FarmBudget(max_runs=..., max_energy=..., max_seconds=..., energy_reserve=0)`:
  todos los límites son finitos; runs/energía son enteros positivos. El reloj
  predeterminado es monotónico; `clock` permite pruebas deterministas.
- `reserve_entry(attempt_id, resource="ENERGY", balance=..., cost=...)` devuelve
  `True` **una sola vez** por intención. Debe ejecutarse antes del clic. Descuenta
  el coste visible de la cuota de sesión, exige saldo suficiente respetando la
  reserva y bloquea otra entrada mientras la anterior no tenga cierre confirmado.
- Repetir la misma intención devuelve `False`, nunca permiso para reintentar.
  Reutilizar su ID con otro coste/recurso es un error. Un clic cuyo efecto es
  incierto permanece reservado: no existe liberación por timeout.
- `finish_run(attempt_id, outcome, closure_confirmed=True)` registra `VICTORY` o
  `DEFEAT` una sola vez; no clica. Un cierre desconocido/ilegible no libera la
  entrada. La derrota bloquea nuevas acciones. Puede registrar el resultado
  después del límite de tiempo, pero no autoriza más entradas.
- `payload()` distingue costes **reservados**, no gasto real confirmado. Ni la
  regeneración ni otro saldo mayor amplían la cuota original.
- Valores ilegibles (`None`), cadenas, booleanos, negativos o no finitos se
  rechazan con `ValueError`, sin modificar los contadores. Nunca convertir una
  ausencia de OCR en cero o en una unidad. Esta entrega solo admite Energy.

## Segunda entrega: cuota compartida de oro, deshabilitada por defecto

- `max_gold=0` y `gold_reserve=0` son los defaults. La cuota no permite gemas,
  Bribe, Recharge, Revive, fabricación ni reposición de objetos escasos.
- `reserve_gold(action_id, currency="GOLD", purpose=..., target=..., balance=...,
  cost=...)` admite solo `PERSUADE` durante una run o `RESTOCK_COMMON` entre runs.
  Ambos descuentan de **la misma cuota finita** y protegen la reserva de oro.
- La cuota **no autoriza objetivos**: el controlador debe comprobar su lista
  explícita de familiares/objetos comunes y el coste total (precio × cantidad).
  `RESTOCK_COMMON` no clasifica la rareza. Habilitar `max_gold` por sí solo no es
  permiso para gastar; el primer runner debe conservar `max_gold=0`.
- `finish_gold(action_id, effect_confirmed=True)` exige confirmar el efecto y
  cierre de la oferta/transacción; no significa que Persuade haya tenido éxito.
  Una persuasión fallida también cuesta oro. No libera ni reembolsa la cuota.
- Un gasto incierto bloquea otro gasto, otra entrada y el cierre contable de
  la run. Repetir su ID no repite el input; cambiar objetivo/coste/propósito con
  el mismo ID es un error. Nunca generar otro ID para saltarse esta guarda.
- Se puede registrar una confirmación después del deadline; no autoriza más
  input. No hay compras ejecutadas ni conexión a la tienda en este componente.

## Integración segura pendiente

El presupuesto no reconoce pantallas, costes, rarezas, inventario ni objetivos.
El controlador debe comprobar modo/ruta, Auto sin gasto nativo, pantalla estable,
captura fresca, coste/multiplicador, foco, cursor, exclusividad y F8, y actuar
**solo si** la reserva devuelve `True`. Comprobar las guardas otra vez antes del
input. Ante `ValueError`, parar/revisar; no crear otro ID o presupuesto para
sortearlo. Usar IDs estables de sesión/ciclo, no un ID nuevo en cada retry.

Es estado en memoria para **un controlador**. Reiniciar no restaura presupuestos
ni permite reanudar una entrada incierta: detener y revisar registros/saldo.
Antes de conectar input, registrar la intención de forma duradera; `Telemetry`
es asíncrono y `emit()` por sí solo no acredita persistencia antes de un crash.
No se certifica protección entre reinicios ni funcionamiento real de dungeons.

Comprobaciones:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_farm_budget.py -v
.venv/bin/python -B -m unittest discover -s tests
```

Los casos son sintéticos; no consumen recursos ni sustituyen una run supervisada.

## Evidencia de esta entrega

- 15 tests propios pasan: cuotas, reservas, deadline exacto, reloj inválido,
  lecturas ambiguas, duplicados, derrota y gastos pendientes.
- 8/8 mutaciones deliberadas detectadas por esos tests, ejecutadas en memoria:
  aceptar booleanos, reautorizar entradas, ignorar reserva/cuotas de sesión,
  permitir el instante del deadline, ignorar gasto pendiente y continuar tras
  derrota. No se modificó el archivo real para esta comprobación.
- Sintaxis y whitespace de los tres archivos nuevos comprobados.
- Suite compartida final: **207 tests ejecutados, 204 pasan y 3 de Windows se
  omiten**. Una ejecución anterior coincidió con un test nuevo que importaba
  `farm_plan` aún ausente. Se comunicó sin tocar archivos ajenos y, tras comprobar
  que la otra sesión añadió la función, se repitió la suite completa con éxito.
- Sin input/captura al juego, compras, instalaciones, commits ni publicación.

Resultados locales de mutaciones:
`/tmp/opencode/bitheroes-budget-mutation-results.json` (no fixture remota).
