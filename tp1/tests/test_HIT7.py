import json
import os
import subprocess
import sys
import time
import unittest
import urllib.request


class TestWindowRegistration(unittest.TestCase):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_inscripcion_y_ventanas(self):
        print("\n--- Iniciando Test de Sistema de Inscripciones con Ventanas (HIT 7) ---")

        # Nodo D: HTTP en 8081, TCP en 9010 (evita colisión con HIT 6)
        env_d = os.environ.copy()
        env_d["TCP_PORT"] = "9010"
        cmd_d = [sys.executable, "-m", "uvicorn", "HIT7.node_d:app", "--host", "127.0.0.1", "--port", "8081"]
        p_d = subprocess.Popen(cmd_d, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=self.BASE_DIR, env=env_d)

        time.sleep(3)  # Esperar a que uvicorn y el servidor TCP arranquen

        node_c_path = os.path.join(self.BASE_DIR, "HIT7", "node_c.py")
        cmd_c = [sys.executable, "-u", node_c_path, "--registry-host", "127.0.0.1", "--registry-port", "9010", "--own-host", "127.0.0.1"]

        print("[Test] Levantando Nodo C1...")
        p_c1 = subprocess.Popen(cmd_c, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2)

        print("[Test] Levantando Nodo C2...")
        p_c2 = subprocess.Popen(cmd_c, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2)

        try:
            # Validar que ambos nodos quedaron inscriptos en la próxima ventana
            print("[Test] Consultando /window/next en Node D...")
            with urllib.request.urlopen("http://127.0.0.1:8081/window/next") as resp:
                data = json.loads(resp.read().decode())
                node_count = data.get("node_count", 0)
                self.assertEqual(node_count, 2, f"Se esperaban 2 nodos en la ventana siguiente, pero hay {node_count}. Respuesta: {data}")

            # Validar que la ventana actual arranca vacía (nadie la pisó aún)
            print("[Test] Consultando /window/current en Node D...")
            with urllib.request.urlopen("http://127.0.0.1:8081/window/current") as resp:
                data = json.loads(resp.read().decode())
                current_count = data.get("node_count", 0)
                self.assertEqual(current_count, 0, f"La ventana actual debería estar vacía, pero tiene {current_count} nodo(s).")

        except urllib.error.URLError as e:
            self.fail(f"Falló la conexión a la API HTTP de Node D: {e}")
        finally:
            p_c1.terminate()
            p_c2.terminate()
            p_d.terminate()
            out_c1, _ = p_c1.communicate()
            p_c2.communicate()
            p_d.communicate()

        # C1 se inscribió pero la ventana actual estaba vacía → no debería haber saludado a nadie
        self.assertNotIn(
            "Saludo enviado",
            out_c1,
            "C1 no debería haber saludado a nadie: se inscribió para la PRÓXIMA ventana.",
        )

        print("✅ Test pasado: Nodo D registró a C1 y C2 en la ventana siguiente correctamente.")


if __name__ == "__main__":
    unittest.main()
