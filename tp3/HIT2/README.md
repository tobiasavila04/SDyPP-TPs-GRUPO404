# TP3 - Grupo 404 | HIT #2: Sobel con Offloading en la Nube (Cloud-Bursting)

Para esta etapa, armamos una **base elástica** para procesar las imágenes del Hit #1. Básicamente implementamos el patrón de *Cloud-Bursting*: si la carga local es demasiada, "desbordamos" el trabajo hacia la nube levantando VMs bajo demanda con Terraform, y cuando terminan, las destruimos para no quemar créditos.

## Arquitectura Híbrida

Como pedía el TP, el enfoque de esta etapa es híbrido (On-premise + Cloud). 

```mermaid
flowchart LR
    subgraph "On-Premise (Local)"
        S[Splitter] -->|Publica chunks| RMQ[(RabbitMQ / Redis)]
        RMQ -->|Entrega resultados| J[Joiner]
    end

    subgraph "Nube (GCP)"
        direction TB
        W1[Worker VM 1]
        W2[Worker VM 2]
        WN[Worker VM N]
    end

    %% Conexiones vía Ngrok o VPN
    RMQ <-->|Túnel Seguro (Ej. Ngrok)| W1
    RMQ <-->|Túnel Seguro (Ej. Ngrok)| W2
    RMQ <-->|Túnel Seguro (Ej. Ngrok)| WN
```

### ¿Por qué lo armamos así?

1. **RabbitMQ / Redis (Local):**
   * Decidimos dejar el sistema de mensajería corriendo local.
   * **El motivo:** El Splitter y el Joiner interactúan un montón con la cola para mandar el peso de la imagen. Si subíamos la cola a la nube, íbamos a tener que subir la imagen completa desde el Splitter por la red, lo cual es lentísimo. Manteniendo la cola local, solo mandamos el tráfico de los pedacitos (chunks) a los workers. Para lograr esto sin exponer los puertos crudos a internet, pasamos la conexión de RabbitMQ por un túnel seguro tipo Ngrok.

2. **Workers (GCP):**
   * Todo el trabajo pesado de CPU (procesar el filtro Sobel) lo mandamos a VMs de Google Cloud que levantamos con Terraform.
   * **El motivo:** Nos da **elasticidad**. Si la cola explota de mensajes, levantamos instancias en GCP en 2 minutos para que absorban el laburo, y apenas se vacía la cola las matamos (`terraform destroy`). Esto cumple con las características de *On-demand self-service* y *Measured service* del paper del NIST.

3. **Orquestador (`orquestador.py` / Terraform):**
   * Armamos un script que corre local para disparar los comandos de Terraform (`apply` para crear, `destroy` para apagar).

## Tradeoffs y el Teorema CAP (Para la defensa)

Tuvimos que pensar bien qué priorizar:
* **Consistencia vs Disponibilidad en RabbitMQ:** RabbitMQ tradicionalmente prioriza la **Consistencia y la Tolerancia a Particiones (CP)**. En nuestro modelo híbrido, internet es el eslabón débil. Si se cae el WiFi de nuestra casa, los workers de Google pierden la conexión. RabbitMQ se da cuenta de esto y no da los mensajes por perdidos, sino que los vuelve a encolar para mantener la consistencia. O sea, prioriza no perder datos por encima de seguir respondiendo a todo bajo fallas severas de red.

## El ciclo de vida de los Workers

Para que quede claro qué pasa cuando corremos el orquestador:
1. **Provisioning**: Terraform le avisa a la API de GCP que nos cree VMs nuevas.
2. **Bootstrap**: Usamos el `metadata_startup_script` en Terraform para que la VM instale Docker ni bien prende.
3. **Deploy**: Ahí mismo le decimos que se baje nuestra imagen `sobel-worker` desde DockerHub.
4. **Join**: Levantamos el contenedor pasándole como variable de entorno la URL de Ngrok que apunta a nuestro RabbitMQ local. Ni bien levanta, arranca a consumir de la cola.
5. **Teardown**: Cuando terminamos, corremos `terraform destroy` para volar las VMs y no gastar plata.
