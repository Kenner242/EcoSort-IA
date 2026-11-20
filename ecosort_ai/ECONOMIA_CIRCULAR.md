# EcoSort AI: de la clasificación a la economía circular

Documento de trabajo para responder al feedback: *"demuestra que la IA mejora la segregación, el reciclaje y la reducción de residuos a relleno, y articula el proyecto con gestores y recicladores"*.

## 1. Diagnóstico honesto
| Fortaleza actual | Brecha a cerrar |
|---|---|
| IA que reconoce residuos (YOLO) | No hay evidencia de que mejore la segregación real |
| Eco-puntos, insignias y ranking | No se mide cuánto material llega a valorización |
| Camino a una estación robótica | Falta definir **a dónde va** cada material después de clasificarlo |
| | Falta gestionar el fin de vida del propio hardware |

**Idea central:** la IA es el medio; el resultado que importa es *kg desviados del relleno sanitario y valorizados*.

## 2. Flujo circular propuesto
```
Persona deposita → EcoSort clasifica → contenedor por material → retiro y pesaje
      → gestor autorizado / recicladores de base → valorización
      → material secundario vuelve a la industria → reporte de trazabilidad a la app
```
| Material | Destino previsto | Qué se necesita |
|---|---|---|
| Plástico | Recicladora (lavado, pellet) | Convenio con gestor o recicladores de base |
| Metal | Fundición / reciclaje de metales | Convenio con gestor |
| Vidrio | Planta de reciclaje de vidrio | Punto de acopio o gestor |
| Papel y cartón | Papelera / planta de cartón | Convenio con gestor |
| Orgánico | Compostaje | Planta o compostera local |
| No aprovechable | Relleno sanitario autorizado | Servicio municipal (meta: reducir este flujo) |
| Electrónicos (incluye el propio sistema) | Gestor autorizado de RAEE | Entrega documentada al final de la vida útil |

En el código esto ya está reflejado en `impact.py` (`CIRCULAR_ROUTES`) y en la pestaña **🌍 Impacto ambiental** de la app. Los socios son *tipos de actores*: no hay convenios firmados, y hay que completarlos con nombres reales.

## 3. Indicadores (KPIs) para demostrar impacto
| Indicador | Fórmula | Cómo se mide |
|---|---|---|
| Tasa de desviación | kg valorizables / kg totales | Pesaje semanal por contenedor |
| Pureza (contaminación) | kg de material correcto / kg del contenedor | Auditoría manual de una muestra |
| Precisión de la IA | % de clasificaciones correctas por clase | `scripts/evaluate.py` + muestra real |
| Kg valorizados con trazabilidad | kg con comprobante del gestor | Guía de entrega / certificado |
| CO₂e evitado (estimado) | kg × factor de emisión del material | `impact.py` con factores locales |
| Participación | usuarios activos y usos por persona | Base de datos de la app |
| Gestión del hardware | % de equipos entregados a gestor RAEE | Registro de bajas |

**Advertencia:** las cifras de CO₂e y peso que muestra la app hoy son *estimaciones* (pesos promedio por unidad y factores de la literatura). Para presentarlas como resultados hay que pesar en el piloto y usar factores locales.

## 4. Diseño de la validación (conecta con `PLAN_CIENTIFICO.md`, Fase 9)
1. **Línea base:** auditoría de composición de los residuos del punto de piloto *sin* EcoSort (1–2 semanas, pesaje por material).
2. **Intervención:** instalar EcoSort con eco-puntos durante 4–6 semanas.
3. **Comparación:** mismos indicadores *con* EcoSort; idealmente un punto de control sin incentivo.
4. **Análisis:** diferencia en tasa de desviación y pureza, con tamaño del efecto y límites del estudio.
5. **Informe:** incluir lo que no funcionó (errores de la IA, contaminación cruzada, abandono de usuarios).

## 5. Alianzas a explorar
- **Gestores de residuos autorizados** y recicladoras para plástico, metal, vidrio, papel y cartón.
- **Asociaciones de recicladores/as de base**: vincularlos como actores centrales aporta inclusión social y trazabilidad.
- **Sistemas de gestión de la Ley REP** (envases y embalajes, aparatos eléctricos y electrónicos, pilas) y la municipalidad local.
- **Planta de compostaje** para la fracción orgánica.
- Para el campus o la comunidad: la unidad de sustentabilidad de la institución.

Marco legal de referencia en Chile: la Ley 20.920 (Marco para la Gestión de Residuos, Responsabilidad Extendida del Productor y Fomento al Reciclaje), que fija metas de recolección y valorización para productos prioritarios como envases, aparatos eléctricos y electrónicos, y pilas. **Verifica las metas y plazos vigentes** directamente en las fuentes oficiales antes de citarlos.

## 5.1 Fin de vida del propio sistema
- Diseñar **modular y reparable** (Raspberry Pi, cámara, servos, fuente reemplazables por separado).
- Elegir componentes de **larga vida** y reutilizar estructura (madera o metal reciclado para los contenedores).
- Llevar un **registro de equipos** y entregar lo que ya no sirva a un gestor autorizado de RAEE, con comprobante.
- Reportar la **huella del hardware** (energía y materiales) junto al impacto positivo, para evitar greenwashing.

## 6. Riesgos y mitigaciones
| Riesgo | Mitigación |
|---|---|
| La IA clasifica mal y contamina el material | Umbral de confianza alto, revisión humana de una muestra, reentrenar con datos propios |
| El material clasificado no se valoriza | Convenio y comprobante con el gestor antes de instalar |
| Incentivos que fomentan fraude (escanear lo mismo varias veces) | Detección de duplicados (ya implementada) y límites diarios |
| Cifras de impacto infladas | Pesar de verdad, mostrar supuestos, reportar intervalos |
| Privacidad | Seudónimos y no guardar fotos de personas |

## 7. Cronograma sugerido
| Semanas | Actividad |
|---|---|
| 1–2 | Reunión con mentor; elegir punto de piloto; contactar 2–3 gestores/recicladores |
| 2–4 | Línea base de residuos; recolectar fotos propias y entrenar el modelo |
| 4–6 | Instalar el piloto; operar con la app |
| 6–10 | Mediciones, trazabilidad con el gestor |
| 10–12 | Análisis, informe y ajustes |

## 8. Preguntas para el Zoom
1. ¿Qué indicador ambiental esperan ver primero: desviación, pureza o CO₂e?
2. ¿Pueden presentarme a un gestor o asociación de recicladores para el piloto?
3. ¿Qué duración y tamaño de piloto consideran suficiente para sostener conclusiones?
4. ¿Cómo prefieren que se reporte el impacto del hardware (RAEE)?
5. ¿Hay un formato de informe o rúbrica de sostenibilidad que deba seguir?

## 9. Borrador de respuesta
> Muchas gracias por el feedback, es muy valioso. Coincido en que hoy el proyecto está más desarrollado en lo tecnológico que en lo ambiental. Ya empecé a incorporar un módulo de impacto (kg desviados, tasa de desviación y CO₂e estimado) y una ruta de economía circular por material, que incluye la gestión de los residuos electrónicos del propio sistema. Me gustaría avanzar con un piloto con línea base y trazabilidad con un gestor autorizado. Con gusto agendamos el Zoom; ¿qué día y hora les acomoda esta semana?

## Fuentes
- [Infografía Ley REP – Ministerio del Medio Ambiente](https://economiacircular.mma.gob.cl/wp-content/uploads/2025/06/Infografia-Ley-REP.pdf)
- [Manual Ley REP – Ministerio del Medio Ambiente](https://economiacircular.mma.gob.cl/wp-content/uploads/2025/06/4.-Manual-Ley-REP.pdf)
- [Decreto de metas de recolección y valorización de pilas y aparatos eléctricos y electrónicos (Carey)](https://www.carey.cl/api/archivo/publican-decreto-que-establece-metas-de-recoleccion-y-valorizacion-de-residuos-de-pilas-y-aparatos-electricos-y-electronicos?lang=es)
