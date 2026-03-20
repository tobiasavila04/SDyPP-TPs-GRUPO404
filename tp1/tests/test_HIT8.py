import json
import os
import subprocess
import sys
import time
import unittest
import urllib.request


class TestGRPCRegistry(unittest.TestCase):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_registro_grpc_y_saludos(self):
        print("\n--- Iniciando Test de Registro y Saludos via gRPC (HIT 8) ---")

        # Nodo D: HTTP en 8082, gRPC en 50052 (evita colisión con otros tests)
        env_d = os.environ.copy()
        env_d["GRPC_PORT"] = "50052"
        cmd_d = [sys.executable, "-m", "uvicorn", "HIT8.node_d:app", "--host", "127.0.0.1", "--port", "8082"]
        p_d = subprocess.Popen(cmd_d, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=self.BASE_DIR, env=env_d)

        time.sleep(3)  # Esperar a que uvicorn y el servidor gRPC arranquen

        node_c_path = os.path.join(self.BASE_DIR, "HIT8", "node_c.py")
        cmd_c = [sys.executable, "-u", node_c_path, "--registry-host", "127.0.0.1", "--registry-grpc-port", "50052", "--own-host", "127.0.0.1"]

        print("[Test] Levantando Nodo C1...")
        p_c1 = subprocess.Popen(cmd_c, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2)  # C1 se registra; D lo guarda; no hay peers aún

        print("[Test] Levantando Nodo C2...")
        p_c2 = subprocess.Popen(cmd_c, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(3)  # C2 se registra, recibe C1 como peer y le envía un saludo gRPC

        try:
            # Validar via HTTP que D tiene 2 nodos registrados
            print("[Test] Consultando /health en Node D...")
            with urllib.request.urlopen("http://127.0.0.1:8082/health") as resp:
                data = json.loads(resp.read().decode())
                registered = data.get("registered_nodes", 0)
                self.assertEqual(registered, 2, f"Se esperaban 2 nodos registrados en D, pero hay {registered}.")

            # Validar via HTTP que /nodes lista a los 2
            print("[Test] Consultando /nodes en Node D...")
            with urllib.request.urlopen("http://127.0.0.1:8082/nodes") as resp:
                data = json.loads(resp.read().decode())
                self.assertEqual(data.get("count", 0), 2, f"El endpoint /nodes debería devolver 2 nodos. Respuesta: {data}")

        except urllib.error.URLError as e:
            p_c1.terminate()
            p_c2.terminate()
            p_d.terminate()
            self.fail(f"Falló la conexión a la API HTTP de Node D: {e}")

        p_c1.terminate()
        p_c2.terminate()
        p_d.terminate()
        out_c1, _ = p_c1.communicate()
        out_c2, _ = p_c2.communicate()
        p_d.communicate()

        # C2 debió recibir respuesta gRPC de C1 al saludarlo
        self.assertIn(
            "Respuesta gRPC",
            out_c2,
            f"C2 no recibió respuesta gRPC de C1. Salida de C2:\n{out_c2}",
        )

        # C1 debió recibir el saludo gRPC de C2
        self.assertIn(
            "Saludo gRPC recibido",
            out_c1,
            f"C1 no registró haber recibido el saludo gRPC de C2. Salida de C1:\n{out_c1}",
        )

        print("✅ Test pasado: Node D registró ambos nodos y C2 saludó a C1 via gRPC correctamente.")


if __name__ == "__main__":
    unittest.main()
