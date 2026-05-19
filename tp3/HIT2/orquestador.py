import os
import subprocess
import sys
import time

def run_command(command, cwd=None):
    """Ejecuta un comando en el shell y devuelve el código de salida."""
    print(f"\n--- Ejecutando: {' '.join(command)} ---")
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        print(f"Error al ejecutar el comando: {' '.join(command)}")
        sys.exit(result.returncode)
    return result.returncode

def main():
    print("Iniciando Orquestador Cloud Bursting - HIT #2")

    if "TF_VAR_project_id" not in os.environ:
        print("ERROR: Debe configurar la variable de entorno TF_VAR_project_id")
        sys.exit(1)
        
    if "TF_VAR_rabbitmq_host" not in os.environ:
        print("ERROR: Debe configurar la variable de entorno TF_VAR_rabbitmq_host con la IP/URL de Ngrok")
        sys.exit(1)

    # Directorio donde está terraform
    terraform_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terraform")

    # Inicializar y aplicar infraestructura
    print("\n[Paso 1] Aprovisionando recursos en la nube con Terraform...")
    run_command(["terraform", "init"], cwd=terraform_dir)
    run_command(["terraform", "apply", "-auto-approve"], cwd=terraform_dir)

    print("\n[INFO] Esperando 60 segundos para que los nodos descarguen e instalen Docker y la imagen del worker...")
    time.sleep(60)

    # Ejecutar lógica del procesamiento
    # Aquí podríamos invocar directamente a joiner.py y splitter.py
    # Pero generalmente se lanzan en terminales separadas, o con subprocess.Popen.
    print("\n[Paso 2] Nodos desplegados. Ahora puedes ejecutar:")
    print("1. En una terminal (HIT1/parte_2_distribuido): python joiner.py")
    print("2. En otra terminal (HIT1/parte_2_distribuido): python splitter.py")
    print("\nPresiona ENTER cuando hayas terminado de procesar las imágenes y desees destruir la infraestructura...")
    input()

    print("\n[Paso 3] Destruyendo la infraestructura elástica...")
    run_command(["terraform", "destroy", "-auto-approve"], cwd=terraform_dir)
    
    print("\nCloud Bursting finalizado exitosamente.")

if __name__ == "__main__":
    main()
