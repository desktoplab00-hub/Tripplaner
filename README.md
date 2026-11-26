================================================================================
                    TRIPPLANNER AI - DOCUMENTACION DEL PROYECTO
================================================================================

1. QUE ES EL PROYECTO
--------------------------------------------------------------------------------
TripPlanner AI es una aplicacion web y un sistema multiagente orientado a la
planificacion de viajes, consulta de vuelos y pronostico del clima, gestion de
viajes e itinerarios y registro de reservas simuladas.

La solucion integra:
- Agentes inteligentes en Amazon Bedrock AgentCore:
  * OrchestratorAgent: coordina las solicitudes del usuario, administra el
    contexto y conecta las herramientas de negocio (trip_tools.py) con el
    backend serverless.
  * FlightsAgent: agente especialista (A2A) conectado al MCP de Kiwi para
    consultar opciones de vuelos y devolver informacion estructurada.
  * WeatherAgent: agente especialista (A2A) conectado al MCP de Open-Meteo para
    consultar el pronostico meteorologico y devolver informacion por dia.
- Backend serverless en AWS (region us-east-2):
  * Amazon API Gateway (HTTP API): https://vuv1fjq9x1.execute-api.us-east-2.amazonaws.com
  * AWS Lambda (Python 3.12):
    - TripsFunction: gestion de viajes (POST /trips, GET /trips, PUT /trips/{tripId})
    - ItinerariesFunction: gestion de itinerarios (POST/PUT/GET /trips/{tripId}/itinerary)
    - ReservationsFunction: gestion de reservas (POST/GET/PUT /reservations, PUT /reservations/{reservationId})
  * Amazon DynamoDB: tabla unica con clave de particion por usuario (pk) y clave
    de ordenamiento (sk) con prefijos TRIP#, ITIN# y RES#.
- Interfaz web (carpeta web/):
  * Aplicacion web de 6 modulos:
    1. Dashboard
    2. Asistente IA (Streaming)
    3. Vuelos
    4. Clima
    5. Mis Viajes e Itinerarios
    6. Gestion de Reservas
  * Servidor local en Python/Flask (web/server.py) que actua como proxy hacia
    Amazon Bedrock AgentCore.
  * Alojamiento web estatico en Amazon S3.

Seguridad y validaciones implementadas:
- El backend y la interfaz no solicitan ni aceptan datos de tarjetas de credito
  o debito (se rechazan campos como card, cardnumber, cvv y tarjeta).
- Las reservas soportan estados como SIMULADA, PENDIENTE y CONFIRMADA.
- La identificacion de usuario utiliza actualmente la cabecera x-user-id (por
  defecto "demo-user"); la autenticacion con Amazon Cognito queda pendiente
  para futuras iteraciones.


2. ESTRUCTURA DE CARPETAS Y ARCHIVOS
--------------------------------------------------------------------------------
TripPlanner/
|-- agentcore/
|   `-- agentcore.json             Configuracion de agentes y variables de entorno
|-- app/
|   |-- FlightsAgent/
|   |   `-- main.py                Agente de vuelos (A2A + MCP Kiwi)
|   |-- OrchestratorAgent/
|   |   |-- main.py                Agente orquestador principal
|   |   `-- trip_tools.py          Herramientas de consulta y escritura
|   `-- WeatherAgent/
|       `-- main.py                Agente de clima (A2A + MCP Open-Meteo)
|-- backend/
|   |-- common.py                  Validaciones, respuestas HTTP y acceso DynamoDB
|   |-- trips.py                   Logica Lambda de viajes
|   |-- itineraries.py             Logica Lambda de itinerarios
|   `-- reservations.py            Logica Lambda de reservas
|-- template.yaml                  Plantilla AWS SAM (DynamoDB, Lambdas, HttpApi)
|-- crear-backend.ps1              Script de generacion del backend serverless
`-- web/
    |-- config.js                  Configuracion de API_URL y USER_ID
    |-- index.html                 Interfaz grafica de 6 modulos
    |-- server.py                  Servidor Flask local hacia AgentCore
    |-- requirements.txt           Dependencias de Python del servidor web
    `-- .venv/                     Entorno virtual Python local


3. COMO EJECUTAR Y DESPLEGAR EL PROYECTO
--------------------------------------------------------------------------------

Requisitos previos:
- Cuenta de AWS configurada en la region us-east-2 con AWS CLI y AWS SAM CLI.
- Python 3.12 y entorno virtual web\.venv listo.
- Herramientas de AgentCore configuradas para el despliegue de agentes.

Paso 1: Generar y desplegar el backend serverless (AWS SAM)
En PowerShell, desde la raiz del proyecto:

  cd C:\Users\Usuario\TripPlanner
  powershell -ExecutionPolicy Bypass -File .\crear-backend.ps1
  sam deploy --guided

Durante el asistente interactivo:
- Stack Name: tripplanner
- AWS Region: us-east-2
- Confirm changes before deploy: N
- Allow SAM CLI IAM role creation: Y
- Disable rollback: N
- Preguntas de funciones sin autenticacion: Y en cada una
- Save arguments to configuration file: Y
- Archivo de configuracion y entorno: Enter para aceptar por defecto

Paso 2: Desplegar los agentes en Amazon Bedrock AgentCore
Desde la raiz del proyecto:

  cd C:\Users\Usuario\TripPlanner
  agentcore deploy

Paso 3: Verificar web/config.js
Asegurar que web/config.js contenga:

  window.CONFIG = {
    API_URL: "https://vuv1fjq9x1.execute-api.us-east-2.amazonaws.com",
    USER_ID: "demo-user"
  };

Paso 4: Ejecutar el servidor local (web/server.py)
Desde PowerShell en la carpeta web:

  cd C:\Users\Usuario\TripPlanner\web
  .\.venv\Scripts\python.exe server.py

Luego abrir en el navegador:
  http://127.0.0.1:5000

Paso 5: Publicar la interfaz estatica en Amazon S3
Desde PowerShell en la raiz del proyecto:

  cd C:\Users\Usuario\TripPlanner
  $bucket = "tripplanner-frontend-090587344601"
  aws s3 mb "s3://$bucket" --region us-east-2
  aws s3 website "s3://$bucket" --index-document index.html
  aws s3api put-public-access-block --bucket $bucket --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

  $policy = @"
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::$bucket/*"
      }
    ]
  }
  "@
  $policy | Out-File -Encoding ascii policy.json
  aws s3api put-bucket-policy --bucket $bucket --policy file://policy.json
  Remove-Item policy.json

  aws s3 sync ".\web" "s3://$bucket" --exclude ".venv/*" --exclude "*.py" --exclude "requirements.txt" --exclude "__pycache__/*"

URL del sitio web estatico en S3:
  http://tripplanner-frontend-090587344601.s3-website.us-east-2.amazonaws.com

Nota: Si se consulta el chat con el agente desde la URL de S3, mantener
encendido web/server.py en http://127.0.0.1:5000, ya que las peticiones
/api/chat se dirigen al proxy local cuando no se esta en localhost.