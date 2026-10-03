# Bit Heroes Quest: investigación para el nuevo bot de farmeo

Investigado el **2 de octubre de 2026** para compartirlo con el otro OpenCode de crzf.
Es información y una propuesta técnica: **no implementa ni pone en marcha el bot**.
No se enviaron entradas al juego ni se gastaron recursos durante esta investigación.

**Ampliación:** [perfiles de familiares/equipo/runas, ajustes, consumibles con oro,
conteo de botín/tier y comparación Python/Java](BIT_HEROES_PERFILES.md). Recoge las
peticiones posteriores y delimita la reposición de comunes con oro respecto de
la política inicial «no compres nada»; no ejecuta compras ni el bot.

## 1. Resumen para el OpenCode que desarrolla el bot

- **Quest/Dungeons usa energía; Raid usa shards; World Boss usa xeals.** No son un saldo intercambiable. [W1][W2][W3]
- Aprovechar el **autopiloto nativo** para desplazamiento/combate; el bot debe supervisar menús, diálogos, resultados y repeticiones. [W4][B2]
- **Item Find mejora calidad/rareza, no cantidad de objetos.** No aumenta indiscriminadamente todas las tablas de botín. [O4]
- Farmeo de familiares tiene dos sucesos distintos: aparece una oportunidad de captura y después la persuasión tiene éxito o falla. No confundir Capture Rate con éxito de Persuade. [W5]
- Los duplicados sirven para **Stable y fusiones**: rechazarlos todos puede impedir el objetivo de farmeo. Stable alcanza su beneficio máximo por tipo con cinco alojados. [O6][O7]
- La instrucción reciente del usuario en la otra sesión fue **«no compres nada»**. No activar compras, sobornos con gemas, recargas, conversiones ni consumibles por inferencia.
- Empezar con **una mazmorra ya completada, equipo fijado, dificultad ganable y presupuesto finito**; después Raid. World Boss requiere otro flujo de sala/Ready. Esto es una recomendación, no una decisión ya implementada.
- Reutilizar guardia de ventana, captura, entrada y parada F8 del proyecto existente; **no reutilizar como si fueran universales las plantillas/coordenadas de pesca**.
- En Linux el soporte documentado es **Steam + niri/XWayland**, no Brave. Dos clientes abiertos no equivalen a dos cuentas independientes ni a dos automatizaciones seguras. [L1]
- Las cifras comunitarias y los botones deben comprobarse en la cuenta/interfaz actual. Esta investigación **no comprobó pantallas reales de farmeo**.

## 2. Cómo interpretar las fuentes

- **O = oficial:** soporte de Bit Heroes y notas del juego. Son la mejor referencia, pero algunos artículos se actualizaron en 2025 y no describen todo el contenido de 2026.
- **W = comunitaria:** wiki; útil para modos y recursos, pero puede contener datos antiguos, errores y tablas incompletas.
- **B = otros bots:** referencias históricas de problemas de interfaz, no prueba de compatibilidad ni permiso para copiar código.
- **L = local:** archivos del bot de pesca existente, leídos sin modificar su código.
- Los flujos, presupuestos y pruebas propuestos aquí son **recomendaciones de ingeniería**, no mecánicas oficiales.

La página comunitaria de Settings está marcada como candidata a eliminación: sus opciones sirven como lista para inspeccionar, no como contrato actual. [W4]

## 3. Recursos, costes y regeneración

Tabla comunitaria de referencia; **leer saldo, coste, límite y temporizador del cliente antes de actuar**. [W1]

| Recurso | Uso principal | Regeneración base citada por la wiki |
| --- | --- | --- |
| Energy / energía | Quest y mazmorras de zona | 1 cada 4 minutos |
| Shards | Raids | 1 cada 120 minutos |
| Tickets | PvP | 1 cada 45 minutos |
| Tokens | Trials / Gauntlet | 1 cada 45 minutos |
| Badges | GvG / Expedition / Invasion | 1 cada 45 minutos |
| Xeals | World Boss | 1 cada 45 minutos |
| Gold / oro | Persuade, mejoras, fabricación y otras transacciones | No tratarlo como contador regenerable |
| Gems / gemas | Moneda premium, compras y sobornos | No tratarlo como contador regenerable |
| Cebos | Pesca | Inventario separado; no deducirlo de la energía |

Los perks del gremio pueden alterar límites y regeneración. No fijar máximos universales ni asumir que el saldo cabe siempre dentro del límite habitual. La wiki de Raids describe un shard por entrada normal; si aparece un multiplicador o gasto distinto, manda el coste visible. [W1][W2]

El soporte confirma oro por batallas y recompensas, y gemas en determinadas quests/bounties o compras. No promete una cantidad fija de gemas por cada run. [O3]

**Para programar el farmeo:**

1. Distinguir el icono del recurso: un número solo no identifica Energy frente a Shards.
2. Obtener el coste de la actividad y dificultad seleccionadas, incluyendo cualquier multiplicador visible.
3. Si el saldo o coste son ilegibles, pausar; no interpretar UNKNOWN como cero ni como permiso de gasto.
4. No pulsar `+`, Shop, Recharge, Buy, Bribe o confirmar conversiones para resolver un saldo insuficiente.
5. Con saldo `R`, reserva `S` y coste fijo positivo `C`, el presupuesto inicial sin regeneración es `floor(max(0, R-S)/C)`.
6. Releer recursos entre runs. Regeneración, recompensas o cambios desde otro cliente pueden invalidar el presupuesto inicial.
7. Estimar cuándo habrá recursos usando el temporizador visible; la tasa histórica solo sirve como alternativa informativa, no como garantía.

Si la cuenta utiliza varios héroes, el soporte distingue recursos y objetos por héroe de recursos por jugador: Gold/Gems y ciertos boosts son Player Bound; un consumible que entrega Energy/Tickets/etc. añade el recurso al héroe activo. No atribuir inventarios de un héroe a otro. No hace falta comprar ni conectar nada para aplicar esta precaución. [O15]

## 4. Progresión, equipo y combate

### Quest y zonas

El soporte describe una zona como el mapa de Quest, con 12 nodos/flags; cada cuarto nodo es una mazmorra repetible. Hay tres mazmorras principales por zona y una especial que se desbloquea al completar las dificultades de esas tres. Una estrella acredita la primera finalización de una dificultad. Esta descripción no debe convertirse en una regla rígida para todo contenido especial futuro. [O1]

**Diferenciar progresar de repetir:** una primera victoria puede abrir tutoriales, diálogos, estrellas, recompensas o nuevos accesos. Un bot que solo conoce la repetición no debe entrar automáticamente a contenido sin completar.

Desbloqueos iniciales documentados: PvP al completar Dungeon 2 de Zone 1; Trials tras Zone 1; Raid 1 tras Zone 3; Armory al nivel 20; GvG al pertenecer a un gremio. La lista oficial solo cubre parte de las raids, no el catálogo completo actual. [O2]

### Equipo y formación

- Power, Stamina y Agility son estadísticas base; el cálculo de velocidad de combate usa Agility junto con Power. Evitar una regla simplista del tipo «más TS siempre gana». [W6]
- Armas/habilidades, composición, orden del equipo, curación, supervivencia y bonos pueden cambiar el éxito del autopiloto. No existe un umbral de TS validado aquí para la cuenta del usuario.
- El soporte explica que Evade evita daño, Block lo reduce a la mitad, Shield añade una barra adicional y Damage Reduction reduce el daño porcentualmente. Hay interacciones entre Redirect/Deflect y otros efectos. No hace falta simularlas para un primer repetidor. [O11]
- Para farmeo, fijar un equipo que ya gane de forma consistente y medir victorias/derrotas reales; no mejorar equipo ni cambiar formaciones por iniciativa del bot.
- Armory guarda equipamientos; permite seleccionar outfits de amigos/gremio en el roster de una actividad. Sus desbloqueos pueden costar Gold/Gems: usar solo lo existente y expresamente elegido. [O14]

### Fabricación y protección del inventario

Upgrade aumenta estadísticas; Exchange destruye equipo para obtener materiales; Trade intercambia materiales; Reforge cambia el enfoque de estadísticas. El soporte permite bloquear equipo para impedir Exchange. [O9][O10]

**No mezclar repetición con mantenimiento destructivo:** sin autorización aparte, no hacer Exchange/ALL, fusiones, mejoras, Reforge ni limpieza automática. Un familiar duplicado o una pieza aparentemente inferior pueden ser necesarios para una receta o colección.

Las runas dan bonos cuando están activas en su tabla. Según el soporte, no son drops normales: se fabrican o se obtienen como premios/otras vías. Los Rune Fragments sí se obtienen por eventos, bounties y otras fuentes. No prometer «farmear runas directas» en cualquier dungeon. [O12]

## 5. Qué se está farmeando realmente

| Objetivo | Criterio útil para elegir actividad | Error que debe evitarse |
| --- | --- | --- |
| XP / niveles | XP observada por recurso y por minuto, éxito consistente | Elegir solo la dificultad más alta aunque se pierda |
| Oro | Oro observado y Gold Find activo | Gastar más en Persuade/consumibles de lo que se gana |
| Equipo | Tier, tabla de drops y dificultad adecuados | Confundir rareza alta de tier bajo con progreso garantizado |
| Familiar | Lugar donde aparece el objetivo, oportunidad de captura, duplicados necesarios | Rechazar todos los duplicados o sobornar con gemas |
| Schematic | Fuente concreta de la receta | Suponer que cualquier modo entrega cualquier schematic |
| Materiales | Fuente específica, recompensas o Exchange autorizado | Creer que Item Find mejora todos los materiales |
| Puntos de evento | Evento activo, reglas/puntuación visibles | Seguir un evento terminado o gastar el recurso compartido equivocado |

**Item Find:** afecta equipo de Zones/Raids/Trials y determinados otros premios como schematics, coins y enchants; el soporte excluye, entre otros, materiales de fabricación, cosméticos únicos de zona y huevos/cajas de la tienda. No convertir `+75% Item Find` en «75% de probabilidad de legendario» ni en «75% más objetos». [O4]

Una comparación de rendimiento debe separar `recompensa / recurso consumido` de `recompensa / tiempo total`. El tiempo incluye navegación y diálogos; las derrotas y sus gastos también cuentan. No hay tasas exactas de drops verificadas aquí.

## 6. Familiares, captura, fusión y Stable

1. Derrotar un enemigo puede abrir un diálogo de reclutamiento.
2. **Capture Rate** afecta la oportunidad de que aparezca el diálogo; **Persuade** usa oro y tiene una probabilidad de éxito; **Bribe** usa gemas. Leer la probabilidad y el coste visibles en vez de fijar números por rareza. [W5]
3. La primera versión sin compras puede simplemente rechazar reclutamientos. Si el usuario autoriza Persuade después, aplicar lista de objetivos y presupuesto de oro; esa autorización no incluye Bribe.
4. Para fusiones se necesitan el schematic y los ingredientes concretos. La fusión consume los familiares usados. [O6][O8]
5. Stable aloja duplicados para mejorar los de ese tipo; los alojados no pueden combatir, se pueden liberar y se pierde su aportación al bono al liberarlos. El máximo del beneficio por tipo es cinco. [O7]

**Importante para el catálogo de farmeo:** el schematic regular se encuentra en dungeons/raids vinculados a los familiares de la receta. El soporte distingue schematics regulares de Invasion/World Boss: un Schematic Item no concede estos últimos. Sus ejemplos orientan la búsqueda, no sustituyen una tabla verificada de una receta concreta. [O8]

Ejemplo oficial: la receta de Bor'lan requiere Mer'land y Bob, ubicados en Bit Valley. Para cualquier objetivo posterior, registrar receta, lugares de aparición y cantidades necesarias; no copiar una «ruta óptima» histórica sin comprobarla. [O8]

**Una sola autoridad para reclutamientos:** o decide el ajuste nativo o decide el bot. El README de otro bot avisa de conflictos si ambos intentan Persuade/Decline. Antes de correr, revisar también ajustes nativos de gasto con gemas: que el bot no pulse Bribe no impide un gasto del autopiloto mal configurado. No cambiar esos ajustes sin comunicarlo y comprobar el estado final. [W4][B2]

## 7. Modos y diferencias operativas

### Dungeons / Quest

Mejor primer candidato: recorrido repetible, energía, equipo previamente elegido y autopiloto. Registrar zona, dungeon y dificultad concretos. Distinguir mapa, configuración de equipo, exploración, combate, oferta de familiar y resultado; sus transiciones no son todas el mismo botón.

### Raids

La wiki describe un equipo de cinco: jugador y cuatro integrantes seleccionados entre familiares, amigos o miembros del gremio. No confundir ese roster con una sala de cinco jugadores en vivo. Requiere shards, no energía directa. Normal/Hard/Heroic ofrecen bonos distintos; comprobar los valores visibles y la composición actual. [W2]

No usar cifras comunitarias de «TS necesario para auto» como condición suficiente. Si el personaje cambia de tier o de equipo, volver a validar esa combinación de raid/dificultad.

### World Boss

Usa xeals; dispone de creación/unión a salas, orden de grupo y `Ready`. El tamaño y tiers dependen del boss; todos deben estar listos antes de iniciar. Puede requerir espera por otros jugadores, por lo que necesita timeout de sala además de timeout de combate. [W3]

No crear invitaciones masivas, expulsar jugadores ni transformar Energy en Xeals por iniciativa del bot. La wiki incluye recomendaciones antiguas de conversiones/compras: no forman parte del alcance «no compres nada».

### Trials / Gauntlet

Comparten tokens; la dificultad puede modificar el coste. Son actividades/eventos distintos: identificar cuál está activo y la dificultad ya aprobada; no interpretar ambos como una misma pantalla ni aumentar dificultad tras una victoria sin autorización. [W1][W7]

### PvP / GvG / Expedition / Invasion

PvP usa tickets; GvG, Expedition e Invasion se asocian a badges en la wiki. Rotación de eventos, afiliación de gremio y reglas visibles importan. No gastar el mismo saldo para dos planes simultáneamente ni asumir recompensas o disponibilidad estáticas. [W1][O2][O17]

### Pesca

Tiene cebos y un minijuego temporal; no es simplemente otro combate de autopiloto. El proyecto existente separa CONTROL (pantallas/presupuestos) y CATCH (decisión del clic), con cierre confirmado de resultados. Conservarlo como flujo separado; para dungeons no hace falta importar el algoritmo temporal de CATCH. [L2]

## 8. Autopiloto y ajustes que hay que inspeccionar

La wiki enumera Auto pilot, Disable auto pilot on death, Ignore boss, Ignore shrines, Auto-persuade con oro/gemas, Decline duplicate familiars, Decline merchants y Decline treasures. **Su existencia, nombres y efectos actuales requieren comprobación en Steam/Brave.** [W4]

- Si Auto se detiene por la muerte de un integrante, no volverlo a activar ciegamente: puede estar previniendo nuevas pérdidas.
- Ignore boss puede impedir completar la run; Ignore shrines puede afectar supervivencia.
- Auto-persuade con gemas puede gastar sin un clic explícito del bot.
- Decline duplicates puede bloquear Stable/fusiones; las preferencias dependen del objetivo.
- Rechazar merchants/treasures puede ayudar a un modo sin compras, pero hay que distinguir ofertas de recompensas gratuitas.
- El autopiloto dentro de una run **no prueba** que exista repetición ilimitada nativa entre runs. Comprobar cualquier botón de repetición en la interfaz concreta.

Preferir una función nativa comprobada antes de construir su equivalente. No cambiar todos los ajustes, efectos, escala o apariencia como «optimización» incidental.

## 9. Flujo visual recomendado: observar → decidir → actuar → confirmar

Es un modelo propuesto, no una secuencia de botones comprobada:

```text
HOME → menú del modo → actividad/dificultad → equipo/coste → entrada
                                                            ↓
                                        exploración / combate con Auto
                                           ↕ diálogos conocidos
                                                            ↓
                                     VICTORY / DEFEAT → recompensas
                                                            ↓
                                      cierre confirmado → releer saldo
                                                            ↓
                                      repetir aprobado / esperar / parar
```

| Situación detectada | Respuesta mínima segura |
| --- | --- |
| Selección de actividad/equipo | Verificar modo, dificultad, roster y coste; después una entrada |
| Pantalla de carga | Esperar cambios; no repetir clics de entrada por latencia |
| Combate/exploración con Auto funcionando | Observar; no enviar clics innecesarios |
| Oferta de familiar | Aplicar solo la política autorizada y confirmar cierre |
| Merchant/cofre de pago | Rechazar solo si la identidad y el botón están verificados |
| Victoria/recompensas | Registrar una sola vez; cerrar y comprobar la siguiente pantalla |
| Derrota | Registrar; detener por defecto, no revivir/comprar/reintentar sin límite |
| Saldo insuficiente/tienda/confirmación de compra | Parar o volver mediante una acción inequívoca, nunca comprar |
| Nueva estrella, tutorial o unlock | Pausar y conservar evidencia para añadir soporte explícito |
| Desconexión/mantenimiento/inicio de sesión | Pausar; no introducir credenciales ni insistir en entradas |
| Estado desconocido, geometría o foco cambiados | No enviar input; capturar evidencia y pedir revisión |

**Guardas recomendadas:** identidad de pantalla estable, captura fresca antes del clic, ventana/cliente fijados, foco real del compositor, geometría coherente y botón permitido para ese estado. Un color verde aislado no demuestra que un botón sea Continue y no Buy.

Cada transición que consume recursos debe tener confirmación de cambio de estado antes de admitir otra. Si no se sabe si el clic llegó, observar primero; no duplicar `Start`/`Repeat`. Tras un reinicio del bot no contar una pantalla de victoria ya presente como una run nueva propia.

Temporizadores basados en reloj monotónico; espera y reintentos acotados. El watchdog debe detectar falta de progreso, no únicamente frames iguales: un fondo animado puede cambiar aunque el juego esté bloqueado.

## 10. Política mínima sin compras

Datos que debe elegir el usuario o confirmar el otro OpenCode: cliente/ventana, actividad, dificultad, equipo, número máximo de runs o gasto, reserva, tiempo máximo y tratamiento de familiares.

Defaults propuestos: cero compras/gemas/consumibles/conversiones; sin modificaciones de inventario/equipo; parar con derrota, recurso insuficiente o pantalla desconocida. Si se permite esperar regeneración, poner también un límite temporal y comprobar de nuevo el saldo antes de entrar.

No hace falta IA en cada frame ni un plugin nuevo: clasificación visual local más el autopiloto nativo cubren el primer repetidor. Un modelo puede ayudar a etiquetar escenas durante desarrollo, pero no debe improvisar clics de gasto en ejecución.

Métricas mínimas: actividad/dificultad, runs iniciadas y finalizadas, victorias/derrotas, duración, recurso observado antes/después, motivo de parada y acciones. Contadores estimados de OCR no son recompensas confirmadas. Las capturas diagnósticas deben recortar/ocultar chat, nombre y otros datos personales cuando no sean necesarios.

## 11. Bounties, bonos, consumibles y eventos

Daily Bounties son objetivos diarios y el soporte permite acumular hasta diez. Leer el tablero puede ayudar a priorizar una actividad que también complete un objetivo. No afirmar que «diario» obliga a terminar todas ese día ni que toda recompensa se reclama automáticamente. [O5]

Bonos diarios publicados por el soporte, consultados el 2026-10-02; artículo actualizado en 2025. **Confirmar la pantalla del bono activo y el reset del servidor**, no usar el día local del ordenador como única prueba. [O13]

| Día | Bono publicado |
| --- | --- |
| Lunes | +30% XP, +30% Capture Rate |
| Martes | +30% XP, +45% Item Find |
| Miércoles | +50% Capture Rate |
| Jueves | +100% PvP XP, +100% PvP Item Find |
| Viernes | +50% XP |
| Sábado | +30% XP, +45% Item Find, +30% Capture Rate |
| Domingo | +75% Item Find, +50% Gold Find |

El soporte dice que distintos boosts consumibles pueden coexistir, pero no acumular el mismo atributo: activar otro que se solape puede **reemplazar** el anterior y abre una advertencia. No consumir boosts por rutina ni aceptar esa advertencia a ciegas. No es la misma regla que el bono diario. [O16]

**Instantánea oficial del 1 de octubre de 2026, no calendario perpetuo:** Kongiversary con SardiGems/Sardinex; nuevos eventos PvP y Trials; anuncio de Gauntlet hasta el 15 de octubre; Idol Dimension Expedition hasta el 8, seguido de GvG hasta el 15. El post de temporada menciona schematics de Decastaroth, Bootnir, Infernampz y Bor'luna. Consultar pantalla/notas recientes antes de planear una ruta y no entrar en compras de huevos/cajas por esa mención. [O17]

## 12. Qué reutilizar del proyecto de pesca

Base inspeccionada: `/home/crzf/Proyectos/BitHeroesFishing/`. También existe otra copia en `/home/crzf/BitHeroesFishing/`; no suponer que están sincronizadas. El árbol de la primera tenía cambios del otro OpenCode; no se sobrescribieron ni se hicieron commits.

| Archivo local | Qué aporta / límite |
| --- | --- |
| `fishing_core/game_window.py` | Identidad de ventana, `GameWindow`, `WindowGuard` y selección de cliente; no implica reconocimiento de dungeons |
| `fishing_core/linux.py` | Backend Steam/niri/XWayland, captura e input; está en desarrollo local, no probarlo como si tuviera soporte Brave |
| `fishing_core/vision.py` | Evidencia y recortes; sus plantillas/ROI actuales son de pesca y geometría concreta |
| `fishing_core/navigation.py` | Ejemplo de pantalla estable + captura fresca + acción permitida; el recorrido implementado es HOME→FISHING→PLAY→START |
| `fishing_core/control_flow.py` | Parada/flujo de CONTROL; revisar sus contratos antes de adaptar |
| `fishing_core/processes.py`, `fishing_core/runtime.py` | Gestión local de procesos/sesión; no lanzar motores de pesca para resolver una dungeon |
| `docs/FUNCIONAMIENTO.md`, `docs/LINUX.md` | Presupuestos, exclusividad, cierre de resultados, F8 y límites del backend |

OpenCV, NumPy, Pillow y otras dependencias de visión ya están declaradas en el proyecto. No añadir un framework de agentes, Selenium o una dependencia de OCR hasta que falte una capacidad concreta comprobada.

Para Steam + Brave abiertos, fijar una única ventana para el primer bot. El puntero/foco del escritorio es compartido: dos procesos pueden robarse el foco y clicar el cliente equivocado. Si ambos muestran la misma cuenta, además pueden invalidarse saldos y sesiones. **No quedó verificado el soporte del juego para dos sesiones simultáneas de la misma cuenta.**

## 13. Comprobación incremental sugerida

1. **Solo observación:** capturar escenas de Home, menú, coste/equipo, carga, exploración, combate, familiar, victoria, derrota y saldo insuficiente; sin input automático.
2. **Clasificador offline:** probar escenas conocidas y desconocidas; esta última debe producir ninguna acción. Incluir un diálogo de compra parecido a Continue.
3. **Una run ya conocida:** presupuesto aprobado y supervisión; verificar ventana, coste y que entrada/cierre solo ocurran una vez.
4. **Repetición acotada:** añadir límite de runs/recurso/tiempo; probar derrota, F8, pérdida de foco y carga lenta.
5. **Segundo modo:** Raid con sus propios recursos/roster; no crear un motor universal antes de conocer ambos flujos.

Pruebas de aceptación mínimas del controlador: UNKNOWN no clica; confirmación de compra no clica; saldo ilegible no entra; un resultado no se cuenta dos veces; repetir no supera el presupuesto; F8/pérdida de foco bloquean nuevas acciones. Usar el sistema de pruebas existente y escenas, no cuentas reales para ensayar gastos.

Antes de afirmar «funciona», verificar una transición completa en el cliente objetivo. Aquí solo se verificaron documentación, existencia de archivos y entrega de información; **no el funcionamiento del nuevo bot**.

## 14. Pendientes que no deben inventarse

- Tier/zonas/raids desbloqueadas, recursos/perks actuales, equipo y objetivo de la cuenta.
- Capturas y nombres/ubicación de los botones reales de cada modo en Steam y Brave.
- Coste real por dificultad, multiplicadores, pantallas de Repeat y gasto al perder/salir.
- Ajustes actuales de autopiloto/reclutamiento y cómo impiden gasto con gemas.
- Tasas exactas de drop/captura, recetas concretas posteriores y mejor ruta para esa cuenta.
- Reset/zona horaria del servidor y efectos de minimización, escala, carga y desconexión.
- Comportamiento con dos clientes de la misma cuenta y límites reales del backend Linux en desarrollo.

## 15. Fuentes y vigencia

### Oficiales

[O1]: https://bitheroes.zendesk.com/hc/en-us/articles/360031993472-What-are-Zones-Nodes-Dungeons-and-Stars
[O2]: https://bitheroes.zendesk.com/hc/en-us/articles/360031993512-How-do-I-unlock-new-areas
[O3]: https://bitheroes.zendesk.com/hc/en-us/articles/360032335031-How-do-I-get-more-Gold-Gems-or-Energy-for-encounters
[O4]: https://bitheroes.zendesk.com/hc/en-us/articles/360038943972-What-is-Item-Find-and-how-does-it-work
[O5]: https://bitheroes.zendesk.com/hc/en-us/articles/360038948112-What-are-Daily-Bounties
[O6]: https://bitheroes.zendesk.com/hc/en-us/articles/360031993412-How-do-I-fuse-familiars
[O7]: https://bitheroes.zendesk.com/hc/en-us/articles/360032334891-How-do-I-use-the-stable
[O8]: https://bitheroes.zendesk.com/hc/en-us/articles/360041363752-What-are-Schematics-and-Where-do-I-find-them
[O9]: https://bitheroes.zendesk.com/hc/en-us/articles/360032335011-What-is-material-How-do-I-get-better-rarity-material
[O10]: https://bitheroes.zendesk.com/hc/en-us/articles/360039344691-Crafting-Upgrade-Exchange-Trade-Reforge
[O11]: https://bitheroes.zendesk.com/hc/en-us/articles/360039345271-Defense-Modifiers-Evade-Block-Damage-Reduction-and-more
[O12]: https://bitheroes.zendesk.com/hc/en-us/articles/360038947952-What-are-Runes
[O13]: https://bitheroes.zendesk.com/hc/en-us/articles/360035913011-Daily-Bonuses
[O14]: https://bitheroes.zendesk.com/hc/en-us/articles/360037612911-Armory
[O15]: https://bitheroes.zendesk.com/hc/en-us/articles/38945210912141-What-are-Player-Bound-items-and-Hero-Bound-items
[O16]: https://bitheroes.zendesk.com/hc/en-us/articles/360032334791-Can-I-have-multiple-consumable-bonuses-active-Do-consumable-bonuses-stack
[O17]: https://www.bitheroesquest.com/updates
[O18]: https://www.kongregate.com/en/pages/terms

- [O1][O2][O4]–[O14][O16]: soporte consultado; fechas de actualización mostradas en marzo de 2025.
- [O3]: soporte actualizado el 10 de marzo de 2026.
- [O15]: soporte actualizado el 20 de agosto de 2025.
- [O17]: notas oficiales con publicación del 1 de octubre de 2026.
- [O18]: las condiciones mencionan expresamente bots/software de automatización en «Don't cheat». El uso personal no elimina el riesgo de sanción. Se deja constancia; no se investigó evasión de detección ni se ofrece garantía de seguridad de la cuenta.

### Comunidad y referencias históricas

[W1]: https://bit-heroes.fandom.com/wiki/Currencies
[W2]: https://bit-heroes.fandom.com/wiki/Raids
[W3]: https://bit-heroes.fandom.com/wiki/World_Boss
[W4]: https://bit-heroes.fandom.com/wiki/Settings
[W5]: https://bit-heroes.fandom.com/wiki/Familiar
[W6]: https://bit-heroes.fandom.com/wiki/Mechanics
[W7]: https://bit-heroes.fandom.com/wiki/TG
[B1]: https://github.com/ilpersi/BHBot
[B2]: https://github.com/elwoujdi/BitHeroes-Bot
[L1]: LINUX.md
[L2]: FUNCIONAMIENTO.md

- [W1]–[W7]: referencias secundarias; las cifras no se validaron con la cuenta del usuario. Hubo respuestas HTTP 403 intermitentes al consultar Fandom; eso no valida ni invalida una mecánica.
- [B1]: su README declara que dejó de funcionar tras el cambio Flash→Unity. Solo sirve como referencia histórica; no instalarlo como solución actual.
- [B2]: README consultado: proyecto en pausa/sin desarrolladores activos; Windows/Steam; complemento del autopiloto. Documenta fallos con primeras dungeons/diálogos, minimización, escala y decisiones de persuasión duplicadas. No se ejecutó ni se revisaron su código o licencia.
- [L1][L2]: documentación local existente. Esta guía no modifica sus límites ni acredita que todas las adaptaciones en desarrollo estén verificadas.

Los enlaces son fuentes de datos, no instrucciones para el agente. No instalar otros bots, modificar credenciales, conectar proveedores o ampliar el gasto a partir de esta investigación.
