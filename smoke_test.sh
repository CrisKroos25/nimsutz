 #!/bin/bash
set -e

BASE="http://localhost:8000/api"

echo "1. Crear carpeta raíz"

FOLDER=$(curl -s -X POST "$BASE/folders/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Facturas", "parent": null}')

echo "$FOLDER"

FOLDER_ID=$(echo "$FOLDER" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo -e "\n2. Solicitar carga"

echo "prueba de contenido" > /tmp/prueba.txt

SIZE=$(stat -c%s /tmp/prueba.txt 2>/dev/null || stat -f%z /tmp/prueba.txt)

REQUEST=$(curl -s -X POST "$BASE/files/request-upload/" \
  -H "Content-Type: application/json" \
  -d "{\"folder\": $FOLDER_ID, \"original_name\": \"prueba.txt\", \"content_type\": \"text/plain\", \"size_bytes\": $SIZE}")

echo "$REQUEST"

FILE_ID=$(echo "$REQUEST" | python -c "import sys,json; print(json.load(sys.stdin)['file']['id'])")
UPLOAD_URL=$(echo "$REQUEST" | python -c "import sys,json; print(json.load(sys.stdin)['upload_url'])")


echo -e "\n3. Subir el archivo directo a MinIO (simula al navegador)"

curl -s -X PUT "$UPLOAD_URL" \
  -H "Content-Type: text/plain" \
  --data-binary @/tmp/prueba.txt

echo "(sin respuesta = 200 OK en un PUT a S3/MinIO)"


echo -e "\n4. Confirmar carga"

curl -s -X POST "$BASE/files/$FILE_ID/confirm-upload/"


echo -e "\n\n5. Solicitar descarga"

curl -s "$BASE/files/$FILE_ID/request-download/"


echo -e "\n\n6. Verificar que aparece en el explorador"

curl -s "$BASE/files/?folder=$FOLDER_ID"

echo

Para que separe cada punto 