#!/bin/bash

set -e

BASE="http://localhost:8000/api"

echo "1. Crear carpeta raíz"

FOLDER=$(curl -s -X POST "$BASE/folders/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Julio 2026", "parent": null}')

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

echo -e "\n3. Subir el archivo directo a MinIO"

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

echo -e "\n\n7. Enviar archivo a papelera"

curl -s -X POST "$BASE/files/$FILE_ID/trash/"

echo -e "\n\n7b. Confirmar que ya no aparece en el explorador normal"

curl -s "$BASE/files/?folder=$FOLDER_ID"

echo -e "\n\n7c. Confirmar que SÍ aparece en la vista de papelera"

curl -s "$BASE/files/?folder=$FOLDER_ID&status=trashed"

echo -e "\n\n7d. Enviar a papelera otra vez"

curl -s -X POST "$BASE/files/$FILE_ID/trash/"

echo -e "\n\n8. Crear un archivo nuevo con el MISMO nombre en la misma carpeta"

REQUEST_2=$(curl -s -X POST "$BASE/files/request-upload/" \
  -H "Content-Type: application/json" \
  -d "{\"folder\": $FOLDER_ID, \"original_name\": \"prueba.txt\", \"content_type\": \"text/plain\", \"size_bytes\": $SIZE}")

echo "$REQUEST_2"

FILE_ID_2=$(echo "$REQUEST_2" | python -c "import sys,json; print(json.load(sys.stdin)['file']['id'])")
UPLOAD_URL_2=$(echo "$REQUEST_2" | python -c "import sys,json; print(json.load(sys.stdin)['upload_url'])")

curl -s -X PUT "$UPLOAD_URL_2" \
  -H "Content-Type: text/plain" \
  --data-binary @/tmp/prueba.txt

curl -s -X POST "$BASE/files/$FILE_ID_2/confirm-upload/"

echo -e "\n\n9a. Intentar restaurar el archivo original"

curl -s -X POST "$BASE/files/$FILE_ID/restore/"

echo -e "\n\n9b. Restaurar el archivo original con un nombre nuevo"

curl -s -X POST "$BASE/files/$FILE_ID/restore/" \
  -H "Content-Type: application/json" \
  -d '{"new_name": "prueba_restaurada.txt"}'

echo -e "\n\n9c. Confirmar que ambos archivos ya aparecen disponibles"

curl -s "$BASE/files/?folder=$FOLDER_ID"

echo -e "\n\n10a. Enviar el segundo archivo a papelera"

curl -s -X POST "$BASE/files/$FILE_ID_2/trash/"

echo -e "\n\n10b. Eliminar definitivamente"

curl -s -X DELETE "$BASE/files/$FILE_ID_2/permanent/"

echo "(sin respuesta = 204 No Content)"

echo -e "\n\n10c. Confirmar que ya no aparece ni en explorador ni en papelera"

curl -s "$BASE/files/?folder=$FOLDER_ID"

echo ""

curl -s "$BASE/files/?folder=$FOLDER_ID&status=trashed"

echo