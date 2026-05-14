Hit #4 — Flip-Y y Flip-X
Concepto: manipulación de UV como mecanismo de transformación
El insight fundamental de este hit es que cualquier transformación geométrica de la imagen puede lograrse únicamente modificando las coordenadas UV antes de samplear la textura. No se mueven píxeles: se cambia desde dónde se lee la textura para cada píxel de salida. La imagen en sí no se toca; lo que cambia es el mapeo entre píxel de destino y texel de origen.
Esto es exactamente la potencialidad de UV que se mencionó en el Hit #1: al trabajar en espacio normalizado [0, 1], cualquier transformación matemática (inversión, escala, rotación, distorsión) se aplica de forma universal, independientemente de la resolución.

Flip-Y (volteo vertical / cabeza abajo)
Para voltear verticalmente, el píxel que antes leía de uv.y ahora debe leer de 1.0 - uv.y. El extremo superior de la pantalla (uv.y = 1.0) pasa a leer desde y = 0.0 de la textura, y viceversa.
glslvoid mainImage( out vec4 fragColor, in vec2 fragCoord ) {
    vec2 uv = fragCoord.xy / iResolution.xy;

    // Flip vertical: invertir el eje Y
    uv.y = 1.0 - uv.y;

    fragColor = texture(iChannel0, uv);
}
¿Qué ocurre?
El eje X no se toca (uv.x queda igual), por lo que la imagen conserva su orientación horizontal. Solo el eje Y se invierte: la fila de píxeles que antes correspondía a y=0 (abajo) ahora se muestra arriba, y la que correspondía a y=1 (arriba) se muestra abajo.
Captura de pantalla

![alt text](screenshoots/hit4-flipY.png)


Flip-X (volteo horizontal / espejo)
Análogo al Flip-Y, pero sobre el eje X: uv.x = 1.0 - uv.x. Lo que estaba a la derecha pasa a estar a la izquierda.
glslvoid mainImage( out vec4 fragColor, in vec2 fragCoord ) {
    vec2 uv = fragCoord.xy / iResolution.xy;

    // Flip horizontal: invertir el eje X
    uv.x = 1.0 - uv.x;

    fragColor = texture(iChannel0, uv);
}
¿Qué ocurre?
El píxel de la columna más a la izquierda (uv.x = 0.0) ahora lee desde el extremo derecho de la textura (uv.x = 1.0), y viceversa. El resultado es una imagen en espejo — el efecto típico de una cámara "selfie". El eje Y no se toca.
Captura de pantalla

![alt text](screenshoots/hit4-flipX.png)


Flip-X + Flip-Y simultáneo
Se pueden combinar ambas inversiones en una sola línea:
glsluv = 1.0 - uv;
GLSL promueve el escalar 1.0 a vec2(1.0, 1.0) y realiza la resta componente a componente, invirtiendo ambos ejes al mismo tiempo. El resultado es equivalente a una rotación de 180°.

Potencialidad de UV — ampliación
La manipulación de UV no se limita a inversiones. Dado que UV es un espacio matemático continuo [0, 1]², cualquier función f: ℝ² → ℝ² aplicada sobre uv antes del texture() produce una transformación de imagen diferente:
Operación sobre uvEfecto visualuv.y = 1.0 - uv.yFlip verticaluv.x = 1.0 - uv.xFlip horizontal (espejo)uv = 1.0 - uvRotación 180°uv = uv * 2.0Zoom out (imagen se ve más pequeña, aparece repetida si el sampler usa wrap)uv = uv * 0.5 + 0.25Zoom in al centrouv -= 0.5; uv = mat2(cos(a),-sin(a),sin(a),cos(a)) * uv; uv += 0.5Rotación arbitraria de ángulo auv.x += sin(uv.y * freq) * ampEfecto ola / distorsión sinusoidaluv = fract(uv * N)Tiling: repetir la imagen N×N veces
Todo esto ocurre antes de llamar a texture() — el GPU ni siquiera sabe que la imagen fue transformada; simplemente lee desde las coordenadas que el shader le indica. Esta es la razón por la que UV es el espacio natural de trabajo para cualquier efecto de imagen en shaders.