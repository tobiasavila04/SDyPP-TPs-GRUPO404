# Hit #1 — Pixel Shaders y Pipeline de Renderizado

---

## 1. Tipos de Shaders

Un **shader** es un programa que corre directamente en la GPU y determina cómo se procesa y colorea la geometría o los píxeles de una escena. Existen varios tipos:

### Vertex Shader
Opera sobre cada vértice de la geometría 3D de forma individual. Su trabajo es transformar la posición del vértice desde el espacio del objeto hacia el espacio de proyección (la pantalla), aplicando transformaciones de modelo, vista y proyección. También puede calcular iluminación por vértice o preparar datos para etapas posteriores. Se ejecuta una vez por cada vértice enviado al pipeline.

### Pixel Shader (Fragment Shader)
Opera sobre cada fragmento (candidato a píxel) que resulta de la rasterización. Su responsabilidad es calcular el color final de ese píxel en pantalla, teniendo en cuenta texturas, iluminación, sombras, etc. Es el shader que nos concierne en esta práctica: puede operar sobre imágenes 2D puras, sin necesitar escena 3D alguna, lo que lo hace ideal para filtros, efectos de post-procesamiento y generación procedural de imágenes.

### Geometry Shader
Se ejecuta después del Vertex Shader y recibe primitivas completas (triángulos, líneas, puntos) como entrada. Puede emitir nuevas primitivas o descartar las existentes, lo que permite efectos como generación de partículas, extrusión de sombras o renderizado en un solo paso a un cubemap.

### Compute Shader
No forma parte del pipeline gráfico clásico sino que es de propósito general (GPGPU). Permite correr kernels de cómputo arbitrario en la GPU, compartiendo recursos con los shaders gráficos. Es la base de técnicas modernas como física de partículas, ray tracing en tiempo real o algoritmos de IA sobre GPU.

### Tessellation Shaders (Hull + Domain)
Controlan la subdivisión de geometría de baja resolución en geometría de alta resolución directamente en la GPU, útil para LOD (Level of Detail) adaptativo.

> **Nota relevante**: los Pixel Shaders son el único tipo de shader que puede actuar como postprocesador o filtro sobre una imagen 2D, sin requerir escena 3D. Esto los convierte en la herramienta central tanto para efectos de renderizado como para computación visual de propósito general sobre imágenes.

---

## 2. Pipeline de Renderizado (WebGL)

El pipeline de renderizado es la secuencia de etapas que la GPU ejecuta para transformar datos geométricos en píxeles en pantalla. En WebGL, el pipeline se puede describir en **6 pasos principales**:

```
[1] Vertex Specification  →  [2] Vertex Shader  →  [3] Primitive Assembly & Rasterization
        →  [4] Fragment (Pixel) Shader  →  [5] Per-Fragment Tests  →  [6] Framebuffer Output
```

### Paso 1 — Vertex Specification (CPU → GPU)
El desarrollador define la geometría en la CPU: arrays de vértices con atributos como posición, normales y coordenadas de textura. Estos datos se suben a la memoria de la GPU en Vertex Buffer Objects (VBOs). Es la etapa de preparación y carga de datos; ocurre en CPU y es de naturaleza **3D** (los datos son posiciones en espacio 3D).

### Paso 2 — Vertex Shader (programable)
La GPU ejecuta el Vertex Shader una vez por cada vértice. Transforma las posiciones del espacio del objeto al espacio de clip (coordenadas normalizadas entre −1 y 1) aplicando matrices de modelo, vista y proyección. Etapa **3D**: trabaja con coordenadas tridimensionales.

### Paso 3 — Primitive Assembly & Rasterización (fija)
Los vértices transformados se ensamblan en primitivas (triángulos, líneas, puntos). Luego la rasterización convierte esas primitivas matemáticas en fragmentos discretos — candidatos a píxeles en la grilla 2D de la pantalla. Incluye clipping (descartar lo que está fuera del frustum) y culling (descartar caras ocultas). A partir de aquí el procesamiento pasa al dominio **2D**.

### Paso 4 — Fragment Shader / Pixel Shader (programable)
La GPU ejecuta el Fragment Shader una vez por cada fragmento generado. Calcula el color del píxel usando texturas, iluminación interpolada, efectos, etc. Es el shader central de esta práctica. Etapa **2D**: trabaja sobre la grilla de píxeles resultante de la rasterización.

### Paso 5 — Per-Fragment Tests (fija)
Cada fragmento es sometido a pruebas antes de escribirse en pantalla: depth test (¿está delante de lo ya renderizado?), stencil test, scissor test, alpha blending. Solo los fragmentos que pasan todas las pruebas se escriben al framebuffer. Etapa **2D**.

### Paso 6 — Framebuffer Output
El framebuffer contiene la imagen 2D final resultado de todo el proceso. Se envía a pantalla. Pueden aplicarse operaciones adicionales como gamma encoding, anti-aliasing o dithering. Etapa **2D**.

### Clasificación 3D vs 2D

| Etapa | Dimensión |
|---|---|
| 1. Vertex Specification | 3D |
| 2. Vertex Shader | 3D |
| 3. Primitive Assembly & Rasterización | Transición 3D→2D |
| 4. Fragment Shader | 2D |
| 5. Per-Fragment Tests | 2D |
| 6. Framebuffer Output | 2D |

Los pasos 1 y 2 son puramente 3D: trabajan con vértices en espacio tridimensional. La rasterización es el punto de quiebre donde la geometría 3D se convierte en fragmentos 2D. Del paso 4 en adelante, todo es procesamiento 2D sobre la grilla de píxeles.

---

## 3. Video Post-Processing

### Definición

El **video post-processing** es el proceso de modificar o mejorar una imagen o secuencia de video *después* de que ya fue renderizada o decodificada. No altera la geometría ni la lógica de la escena; actúa sobre el buffer de imagen resultante como si fuera una foto ya tomada.

### Técnicas comunes

- **Escala e interpolación**: redimensionar la imagen con algoritmos como bilinear o bicúbica.
- **Corrección de color**: ajustar brillo, contraste, saturación, balance de blancos.
- **Anti-aliasing temporal (TAA)**: suavizar bordes dentados combinando frames anteriores.
- **Bloom**: simular el resplandor de fuentes de luz brillantes.
- **Depth of Field (DoF)**: desenfocar objetos fuera del plano focal simulando una lente física.
- **Motion Blur**: añadir borrosidad en la dirección del movimiento.
- **Ambient Occlusion (SSAO)**: oscurecer crevices y esquinas para mejorar la percepción de profundidad.
- **Conversión de framerate** (telecine, pull-down): transformar entre diferentes tasas de fotogramas.

### ¿En qué etapa del pipeline se ejecuta?

El post-procesamiento ocurre **después del paso 6 (Framebuffer Output)**, o más precisamente, entre framebuffers: la escena se renderiza primero a un framebuffer en memoria (en lugar de directamente a pantalla), y luego ese buffer se usa como textura de entrada para un segundo Fragment Shader que aplica los efectos. Este proceso puede encadenarse múltiples veces (bloom, luego DoF, luego corrección de color). En términos del pipeline, el post-procesamiento **es en sí mismo una ejecución del Fragment Shader** sobre un quad que cubre toda la pantalla, tomando el framebuffer previo como textura de entrada.

---

## 4. Entradas (Inputs) de ShaderToy

Al crear un nuevo shader en [ShaderToy](https://www.shadertoy.com), el sistema provee las siguientes variables uniformes al Fragment Shader:

| Tipo | Nombre | Descripción |
|---|---|---|
| `vec3` | `iResolution` | Resolución del viewport en píxeles (x=ancho, y=alto, z=pixel aspect ratio, generalmente 1.0) |
| `float` | `iTime` | Tiempo de reproducción del shader en segundos desde que empezó |
| `float` | `iTimeDelta` | Tiempo en segundos que tardó en renderizarse el frame anterior |
| `float` | `iFrameRate` | Frames por segundo actuales del shader |
| `int` | `iFrame` | Número de frame actual desde el inicio (0, 1, 2, …) |
| `float` | `iChannelTime[4]` | Tiempo de reproducción de cada canal de entrada (útil si el canal es un video o audio) |
| `vec3` | `iChannelResolution[4]` | Resolución en píxeles de cada canal de entrada (x=ancho, y=alto, z=profundidad) |
| `vec4` | `iMouse` | Coordenadas del mouse: `xy` = posición actual si el botón izquierdo está presionado; `zw` = posición del último click |
| `samplerXX` | `iChannel0..3` | Canales de entrada configurables: pueden ser texturas 2D, cubemaps, videos, audio, u otro buffer |
| `vec4` | `iDate` | Fecha y hora actual: `x`=año, `y`=mes, `z`=día, `w`=segundos desde medianoche |
| `float` | `iSampleRate` | Tasa de muestreo de audio en Hz (típicamente 44100) |

---

## 5. Salidas (Outputs) del Pixel Shader en ShaderToy

Según el [howto de ShaderToy](https://www.shadertoy.com/howto), la función principal del shader de imagen tiene la siguiente firma:

```glsl
void mainImage( out vec4 fragColor, in vec2 fragCoord );
```

| Tipo | Nombre | Descripción |
|---|---|---|
| `vec2` | `fragCoord` | **Entrada**: coordenadas del píxel actual en píxeles, con valores desde 0.5 hasta (resolución − 0.5). Es la posición del centro del píxel. |
| `vec4` | `fragColor` | **Salida**: color del píxel calculado por el shader. Los cuatro componentes son `(R, G, B, A)` en rango [0.0, 1.0]. El canal alfa es ignorado por el cliente de ShaderToy en el modo imagen estándar, pero se incluye por convención del tipo. |

El shader se invoca una vez por cada píxel de la pantalla. La única responsabilidad del programador es escribir en `fragColor` el color correcto para el píxel indicado por `fragCoord`.

---

## 6. Análisis del Shader "Hello World"

```glsl
void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
    // Normalized pixel coordinates (from 0 to 1)
    vec2 uv = fragCoord/iResolution.xy;

    // Time varying pixel color
    vec3 col = 0.5 + 0.5*cos(iTime+uv.xyx+vec3(0,2,4));

    // Output to screen
    fragColor = vec4(col,1.0);
}
```

### 6.1 ¿Qué representa `uv`?

`uv` (abreviatura de *UV coordinates*) son las **coordenadas normalizadas del píxel**, con valores en el rango [0.0, 1.0] en ambos ejes. Se obtienen dividiendo la posición en píxeles (`fragCoord`) por la resolución total (`iResolution.xy`):

```
uv = fragCoord / iResolution.xy
```

Si `fragCoord` es el píxel de la esquina inferior izquierda, `uv = (0, 0)`. Si es el de la esquina superior derecha, `uv ≈ (1, 1)`.

### 6.2 ¿Por qué trabajar en UV y no en XY?

Trabajar en píxeles absolutos (XY) hace que el shader dependa de la resolución de pantalla. Si la ventana mide 800×600, los valores van de 0 a 800 en X y de 0 a 600 en Y. Si la ventana cambia a 1920×1080, todos los cálculos producen resultados diferentes: los efectos se "escalan" de forma incorrecta, los patrones cambian de tamaño y el código deja de ser portable.

Trabajar en UV elimina esa dependencia: los valores siempre van de 0 a 1 independientemente de la resolución. Un píxel en el centro de la pantalla siempre tiene `uv = (0.5, 0.5)`, sin importar si hay 600 o 2160 píxeles de alto. Esto hace al shader **resolution-independent** y completamente portable.

### 6.3 ¿Cómo se logra la animación si las entradas son "estáticas"?

La clave es `iTime`: es una variable uniforme que la GPU actualiza en cada frame con el tiempo transcurrido en segundos. Aunque las ecuaciones matemáticas del shader son estáticas (no cambian entre frames), `iTime` sí cambia. Al incluirlo dentro de la función `cos()`, el valor del coseno varía continuamente, produciendo colores que oscilan en el tiempo. El shader se ejecuta íntegramente para cada frame (30, 60 o más veces por segundo), y como `iTime` es diferente cada vez, el resultado visual cambia: es una animación. No hay "estado" almacenado entre frames; el shader simplemente es una función `f(tiempo, posición) → color`.

### 6.4 ¿Cómo puede `col` ser `vec3` si la operación parece entre flotantes?

```glsl
vec3 col = 0.5 + 0.5*cos(iTime+uv.xyx+vec3(0,2,4));
```

GLSL realiza **operaciones componente a componente** con sus tipos vectoriales y aplica **promoción de escalares automáticamente**. Analicemos paso a paso:

1. `uv.xyx` — el swizzling convierte el `vec2 uv` en un `vec3` tomando los componentes x, y, x: `vec3(uv.x, uv.y, uv.x)`.
2. `iTime + uv.xyx` — `iTime` es un `float`. GLSL lo promueve a `vec3(iTime, iTime, iTime)` y suma componente a componente, resultando en un `vec3`.
3. `+ vec3(0,2,4)` — suma otro `vec3` componente a componente. El argumento del coseno es `vec3(iTime+uv.x+0, iTime+uv.y+2, iTime+uv.x+4)`.
4. `cos(...)` — GLSL aplica la función `cos` a cada componente del vector, devolviendo un `vec3`.
5. `0.5 * cos(...)` — el escalar `0.5` se promueve y multiplica componente a componente: `vec3`.
6. `0.5 + 0.5*cos(...)` — el escalar `0.5` se promueve nuevamente: suma componente a componente. Resultado final: `vec3`.

El resultado es que cada componente del `vec3` representa un canal de color (R, G, B) con un desfase de fase diferente (`+0`, `+2`, `+4` radianes), lo que produce que los tres canales oscilen en el tiempo de forma desincronizada, generando el efecto arcoíris animado.

### 6.5 Constructores de `vec4`, componentes de `fragColor`, swizzling y propiedades de los tipos vectoriales

#### Constructores posibles de `vec4`

En GLSL, un vector puede construirse de múltiples maneras siempre que la cantidad total de componentes sea exactamente 4:

```glsl
vec4(float, float, float, float)    // 4 escalares
vec4(vec3, float)                   // vec3 + 1 escalar
vec4(float, vec3)                   // 1 escalar + vec3
vec4(vec2, vec2)                    // 2 vec2
vec4(vec2, float, float)            // vec2 + 2 escalares
vec4(float, float, vec2)            // 2 escalares + vec2
vec4(float)                         // repite el escalar en los 4 componentes
vec4(vec4)                          // copia de otro vec4
```

En el shader: `vec4(col, 1.0)` usa el constructor `vec4(vec3, float)`, tomando los tres canales de color de `col` y añadiendo alfa = 1.0 (opaco).

#### Componentes de `fragColor`

`fragColor` es un `vec4` con cuatro componentes:

| Componente | Notación alternativa | Significado |
|---|---|---|
| `.x` o `.r` o `.s` | primer componente | Canal **Rojo** (Red), rango [0.0, 1.0] |
| `.y` o `.g` o `.t` | segundo componente | Canal **Verde** (Green), rango [0.0, 1.0] |
| `.z` o `.b` o `.p` | tercer componente | Canal **Azul** (Blue), rango [0.0, 1.0] |
| `.w` o `.a` o `.q` | cuarto componente | Canal **Alfa** (transparencia), rango [0.0, 1.0]; ignorado por ShaderToy en modo imagen |

#### Swizzling: qué es `uv.xyx`

El **swizzling** es una característica de GLSL que permite construir un nuevo vector seleccionando y reordenando componentes de otro vector de forma arbitraria usando un sufijo de hasta 4 letras. Los componentes pueden repetirse y aparecer en cualquier orden.

```glsl
vec2 uv = vec2(0.3, 0.7);
vec3 a = uv.xyx;   // = vec3(0.3, 0.7, 0.3)
vec3 b = uv.yxy;   // = vec3(0.7, 0.3, 0.7)
vec4 c = uv.xyxy;  // = vec4(0.3, 0.7, 0.3, 0.7)
vec2 d = uv.yx;    // = vec2(0.7, 0.3) — invertido
```

Los nombres de los componentes disponibles son:

| Conjunto | Componentes | Uso semántico habitual |
|---|---|---|
| Geométrico | `.x`, `.y`, `.z`, `.w` | Posiciones, coordenadas espaciales |
| Color | `.r`, `.g`, `.b`, `.a` | Canales de color RGBA |
| Textura | `.s`, `.t`, `.p`, `.q` | Coordenadas de textura |

Los tres conjuntos son intercambiables; son alias del mismo dato. No se pueden mezclar en un mismo swizzle (`.xg` es inválido).

#### Propiedades (swizzles) disponibles por tipo

| Tipo | Componentes accesibles | Ejemplo de swizzle válido |
|---|---|---|
| `vec2` | `.x`/`.r`/`.s`, `.y`/`.g`/`.t` | `uv.yx`, `uv.xx`, `uv.xyx` (→ vec3) |
| `vec3` | + `.z`/`.b`/`.p` | `col.bgr`, `col.zzz`, `col.xyzx` (→ vec4) |
| `vec4` | + `.w`/`.a`/`.q` | `fragColor.rgba`, `fragColor.wzyx`, `fragColor.rg` (→ vec2) |

El swizzle `uv.xyx` en el shader toma un `vec2` y produce un `vec3` repitiendo el componente x — es una forma compacta de construir un vector de 3 dimensiones desde uno de 2, con control preciso sobre qué componentes van en cada posición del resultado.