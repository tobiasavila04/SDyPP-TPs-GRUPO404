Estoy en una Mac con Apple Silicon (ARM) y mi cluster k3d corre en 
  linux/amd64.                                                     
                                                            
  Cuando uso k3d image import, k3d guarda la imagen como tarball y la
   importa con ctr del nodo. El problema es que las imágenes
  multi-arch tienen un manifest index que apunta a varias            
  plataformas, y ctr busca el digest específico de amd64 dentro del
  tarball — pero docker save solo incluyó la arquitectura de mi host 
  (ARM), no la que necesita el nodo. El digest no matchea y falla.   

  Lo que hice para solucionarlo:                                     
  docker pull --platform linux/amd64 <imagen>
  docker save <imagen> | docker exec -i k3d-sobel-server-0 ctr -n    
  k8s.io images import -                                         
                        
  Forzando linux/amd64 en el pull, Docker baja el manifest correcto.
  Y al importar directo con ctr -n k8s.io — saltando k3d — la imagen 
  queda en el namespace que usa k3s.