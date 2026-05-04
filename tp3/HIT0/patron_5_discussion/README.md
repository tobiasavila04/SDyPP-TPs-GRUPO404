# Ejemplo 5 — Análisis Comparativo de Patrones de Mensajería

## Diagramas de Arquitectura

### Patrón 1 — Message Queue (Punto a Punto)
```
[Producer] ──► [Queue: cola_tareas] ──► [Consumer A]
                                   └──► [Consumer B]  (round-robin)
```
- Cada mensaje es consumido **exactamente una vez**
- RabbitMQ distribuye la carga en round-robin entre consumidores
- Si Consumer A cae, los mensajes pendientes pasan a Consumer B (ACK manual)

### Patrón 2 — Pub/Sub (Fan-out)
```
[Publisher] ──► [Exchange: logs_bloques (fanout)]
                         ├──► [Cola exclusiva A] ──► [Subscriber A]
                         ├──► [Cola exclusiva B] ──► [Subscriber B]
                         └──► [Cola exclusiva C] ──► [Subscriber C]
```
- Cada mensaje es entregado **a todos los suscriptores simultáneamente**
- El exchange fanout ignora el routing key
- Colas exclusivas: se destruyen cuando el suscriptor se desconecta

### Patrón 3 — Dead Letter Queue (DLQ)
```
[Producer] ──► [Queue: cola_principal]
                       │
               [Consumer Main]
                       │ nack(requeue=False)
                       ▼
              [DLX Exchange] ──► [Queue: cola_muertos] ──► [Consumer DLQ]
```
- Los mensajes rechazados no se pierden: son redirigidos por la DLX
- El Consumer DLQ audita/alerta sobre los mensajes fallidos
- Garantiza durabilidad incluso cuando el procesamiento falla

### Patrón 4 — Retry con Exponential Backoff
```
[Producer] ──► [cola_principal_retry]
                       │
               [Consumer Retry]
                   ▼ (fallo)
           [cola_espera (TTL)] ──delay→ [cola_principal_retry]  (reintento)
                   ▼ (4° fallo)
             [cola_muertos (DLQ)]
```
- Delay creciente: 1s → 2s → 4s → 8s (TTL en cola intermedia)
- Después de 4 intentos, el mensaje va a la DLQ de forma permanente
- El contador de intentos se propaga en los `headers` AMQP del mensaje

---

## Tabla Comparativa

| Característica | Message Queue | Pub/Sub | DLQ | Retry Backoff |
|---|---|---|---|---|
| Patrón | Punto a Punto | Broadcast | Manejo de errores | Recuperación de fallos |
| Destinatarios | Un solo consumer | Todos los suscriptores | Consumer de auditoría | El mismo consumer (reintento) |
| Escalabilidad | Horizontal (más consumers) | Vertical (más suscriptores) | No aplica | No aplica |
| Persistencia | Sí (hasta ACK) | No (colas exclusivas temporales) | Sí (DLQ durable) | Sí (con TTL) |
| Exchange usado | Default (direct) | Fanout | Direct (DLX) | Default + TTL |
| Caso de éxito | ACK implícito o explícito | ACK automático | ACK en DLQ | ACK al procesar |
| Caso de error | Redelivery (auto_ack=False) | N/A | Redirect a DLQ | Requeue con delay |

---

## ¿Cuándo usar cada patrón?

**Message Queue (P2P):** Ideal para **distribución de carga de trabajo**. Un pool de workers procesa tareas independientes. Ejemplo: procesamiento de imágenes, envío de emails, transcoding de video.

**Pub/Sub (Fan-out):** Ideal para **notificaciones y sincronización de estado**. Múltiples servicios deben reaccionar al mismo evento. Ejemplo: propagación de bloques en una blockchain, invalidación de caché, sincronización de réplicas.

**Dead Letter Queue:** Indispensable en **cualquier sistema productivo**. Evita la pérdida silenciosa de mensajes fallidos y permite auditoría. Ejemplo: pagos rechazados, mensajes malformados, errores de validación.

**Retry con Exponential Backoff:** Para **fallos transitorios**. Servicios que dependen de recursos externos que pueden estar temporalmente no disponibles. Ejemplo: llamadas a APIs de terceros, timeout de bases de datos, rate limiting.

---

## Relación con los patrones de la industria

| Patrón implementado | Equivalente en AWS | Equivalente en GCP |
|---|---|---|
| Message Queue | SQS Standard | Cloud Tasks |
| Pub/Sub | SNS + SQS Fan-out | Pub/Sub |
| Dead Letter Queue | SQS DLQ | Pub/Sub dead-letter topics |
| Retry Backoff | SQS Visibility Timeout + DLQ | Cloud Tasks retry config |

**Referencia:** Hohpe & Woolf (2003) documentan formalmente estos cuatro como patrones canónicos de Enterprise Integration: *Competing Consumers*, *Publish-Subscribe*, *Dead Letter Channel* y *Retry* respectivamente.
