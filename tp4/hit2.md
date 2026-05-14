Hit #2 — Pintando con Código

Quilez es co-creador de ShaderToy, ex Technical Director de sets en Pixar (donde ganó un VES Award por "Brave") y referente mundial en computación gráfica procedural. La obra que documenta el video es un paisaje completo (montañas, cielo, niebla, iluminación) generado sin ningún modelo 3D, textura cargada ni motor gráfico externo: solo fórmulas matemáticas ejecutadas píxel a píxel en un Fragment Shader.
Estructura del proceso
El video descompone la creación del paisaje en tres grandes etapas, aplicadas íntegramente mediante ecuaciones:
1. Escultura del terreno
La forma del terreno se define con una función de altura (heightmap) construida mediante Fractional Brownian Motion (fBm): sumas de capas de ruido (noise) a distintas frecuencias y amplitudes, donde cada capa añade detalle más fino. No hay malla poligonal: la superficie existe solo como una ecuación y = f(x, z). Para recorrer esta superficie desde la cámara se usa raymarching — el rayo avanza paso a paso en el espacio y en cada punto evalúa la función para determinar si intersectó el terreno.
2. Colorización de superficies
El color de cada punto no se lee de una textura sino que se calcula en función de propiedades geométricas del punto:

La normal de la superficie (derivada de la función de altura) determina la inclinación: zonas planas reciben color de tierra o pasto, zonas inclinadas reciben roca.
La altitud modula entre nieve (cimas) y vegetación (valles).
El fBm también se usa para añadir variación de color, simulando patrones orgánicos de musgo, humedad o erosión. Todo esto es aritmética sobre floats, no lookups de textura.

3. Iluminación y atmósfera
La iluminación se construye capa por capa, acumulando contribuciones:

Luz solar directa: producto escalar entre la normal del punto y la dirección al sol.
Sombras suaves: segundo raymarching hacia el sol para detectar oclusión, con un cálculo de "penumbra" basado en la distancia mínima al obstáculo.
Ambient Occlusion (AO): estimación de cuánto cielo "ve" cada punto, oscureciendo crevices y cañadas.
Luz de cielo: contribución difusa proveniente de la semiesfera superior, aproximada con una fórmula basada en la normal.
Niebla atmosférica: el color final se mezcla progresivamente con el color del cielo en función de la distancia al rayo, simulando dispersión de luz.
Color del cielo: gradiente matemático dependiente del ángulo con respecto al sol.

Cada uno de estos efectos es una función matemática pura: senos, cosenos, smoothstep, clamp, interpolaciones lineales y productos escalares.

Conclusiones
1. El pipeline 3D convencional no es el único camino.
La forma tradicional de renderizar una escena es: modelo → rasterización → shading. Quilez demuestra que todo el pipeline puede reemplazarse por un único Fragment Shader que reconstruye la geometría implícitamente mediante raymarching. No hay vértices, no hay triángulos, no hay texturas: solo ecuaciones. Esto rompe el supuesto de que la GPU necesita geometría explícita para producir imágenes fotorrealistas.
2. La matemática es el modelo artístico.
En un flujo de trabajo tradicional, un artista esculpe mallas en un software y un técnico las lleva al motor. Aquí, el artista-programador es la misma persona, y su "pincel" es una función matemática. Ajustar el paisaje significa modificar coeficientes de ruido, exponentes de fBm o umbrales de smoothstep. El conocimiento matemático se convierte directamente en intuición artística, lo que evidencia que la frontera entre arte y matemática es mucho más permeable de lo que se asume.
3. La GPU como motor de computación general, no solo de rasterización.
El shader del paisaje no usa ninguna de las etapas "3D" del pipeline (Vertex Shader, rasterizador): solo el Fragment Shader, ejecutándose en paralelo sobre todos los píxeles. Cada píxel lanza su propio rayo, evalúa la geometría procedural e integra la iluminación de forma independiente. Es un ejemplo concreto de GPGPU disfrazado de gráfico: la GPU realiza cómputo matemático masivamente paralelo, y el "resultado" es una imagen.
4. Compresión extrema de información.
Todo el paisaje — geometría, textura, iluminación — está codificado en unas pocas decenas de líneas de código. Una escena equivalente en un motor tradicional requeriría gigabytes de assets. El enfoque procedural no solo es técnicamente elegante; es una demostración de que la descripción matemática de un fenómeno natural puede ser infinitamente más compacta que su representación discreta.