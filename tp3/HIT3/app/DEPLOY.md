# ¿Cómo levantar todo esto? (Deploy)

A diferencia del Hit 1 donde usábamos `k3d` en local, en este Hit 3 **NO SE LEVANTA NADA A MANO DESDE LA CONSOLA**. Mandamos todo a la nube para no quemar nuestras compus.

## Pasos para ejecutar el TP:


1. Anda a la pestaña **Actions** en este repositorio de GitHub.
2. Buscá el **Pipeline 1** (`terraform_hit3_gke.yml`) y dejá que termine. Esto arma el cluster vacío en Google Cloud.
3. Ejecutá el pipeline de la app (`deploy_k8s_apps.yml`). Esto empuja nuestros contenedores al cluster y deja todo listo esperando.
4. Entrá al **Pipeline 2** (`terraform_hit3_workers.yml`), apretá el botón `Run workflow`, ponele cuántos workers querés (recomendamos 3 o 5 para ver la magia rápido) y dale a `apply`.
5. ¡Listo! Los workers de GCP se van a prender, procesan la imagen, y el resultado se guarda automático.

> **Importante:** Cuando termines de probar, volvé a correr el **Pipeline 2** pero elegí la opción `destroy`. Si te olvidás de hacer esto, las máquinas van a quedar prendidas y ¡nos van a vaciar la tarjeta de la cuenta de Google!

Para ver todos los detalles técnicos de cómo funciona por atrás, lean la `EXPLICACION_DETALLADA.md` que dejamos en la raíz de esta carpeta.
