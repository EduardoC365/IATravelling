import streamlit as st
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, date, timezone
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient

st.set_page_config(page_title='FlightBot', layout='wide')

# Función para obtener el cliente de Azure Language Studio
def get_language_service_client(endpoint: str, key: str):
    return ConversationAnalysisClient(endpoint, AzureKeyCredential(key))

# Cargar configuración desde .env
def load_configuration():
    load_dotenv()
    return os.getenv('LS_CONVERSATIONS_ENDPOINT'), os.getenv('LS_CONVERSATIONS_KEY')

# Analizar la conversación con Azure Language Studio
def analyze_conversation(client, query, project='Travelling', deployment='Travelino'):
    try:
        with client:
            return client.analyze_conversation(
                task={
                    "kind": "Conversation",
                    "analysisInput": {
                        "conversationItem": {
                            "participantId": "1",
                            "id": "1",
                            "modality": "text",
                            "language": "es",
                            "text": query
                        },
                        "isLoggingEnabled": False
                    },
                    "parameters": {
                        "projectName": project,
                        "deploymentName": deployment,
                        "verbose": True
                    }
                }
            )
    except Exception as e:
        return {"error": str(e)}

# Función para extraer entidades detectadas
def extract_entities(entities):
    extracted = {}  # Solo guardaremos las entidades detectadas

    if entities:
        for entity in entities:
            category = entity.get("category", "Desconocido")
            value = entity.get("text", "No especificado")

            # Si la categoría ya está en el diccionario, añadimos más valores
            if category in extracted:
                extracted[category] += f", {value}"
            else:
                extracted[category] = value

    return extracted

def main():
    st.title("FlightBot - Asistente de Vuelos")
    
    # Cargar configuración y cliente
    endpoint, key = load_configuration()
    client = get_language_service_client(endpoint, key)
    
    # Inicializar mensajes en la sesión si no existen
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # 📌 Frases predefinidas
    predefined_phrases = [
        "Quiero ver vuelos para mañana a Madrid",
        "Dime los vuelos disponibles a España",
        "Resérvame vuelos a París para el día 4 de marzo",
        "Quiero que me cancélame todos mis billetes de marzo",
        "Quiero ver los vuelos de Berlín",
        "Muéstrame vuelos económicos a Roma",
        "Necesito un vuelo directo a Londres para el 10 de abril",
        "Encuentra vuelos con escalas a Nueva York",
        "¿Cuáles son las mejores opciones para viajar a Tokio este mes?"
    ]

    # Contenedor de chat
    chat_container = st.container()
    with chat_container:
        st.write("### Chat con el Asistente")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["text"])

    # Entrada del usuario
    user_input = st.chat_input("Escribe tu mensaje...")

    if user_input:
        st.session_state.messages.append({"role": "user", "text": user_input})

        result = analyze_conversation(client, user_input)

        if "error" in result:
            response = f"❌ Error en la consulta: {result['error']}"
        else:
            prediction = result["result"]["prediction"]
            top_intent = prediction["topIntent"]
            entities = prediction.get("entities", [])

            # Extraemos correctamente las entidades detectadas
            extracted_entities = extract_entities(entities)

            # Construimos la respuesta dinámica solo con las entidades detectadas
            response = f"🧠 **Intención detectada:** {top_intent}\n"
            for key, value in extracted_entities.items():
                response += f"🔹 **{key}:** {value}\n"

        # Guardar respuesta en el estado de la sesión
        st.session_state.messages.append({"role": "assistant", "text": response})
        st.rerun()  # 🔄 Actualizar la UI

    # 📌 Mostrar respuesta en el lateral
    with st.sidebar:
        st.write("### Frases sugeridas")
        for phrase in predefined_phrases:
            if st.button(phrase):
                st.session_state.messages.append({"role": "user", "text": phrase})
                result = analyze_conversation(client, phrase)
                
                if "error" in result:
                    response = f"❌ Error en la consulta: {result['error']}"
                else:
                    prediction = result["result"]["prediction"]
                    top_intent = prediction["topIntent"]
                    entities = prediction.get("entities", [])

                    extracted_entities = extract_entities(entities)
                    response = f"🧠 **Intención detectada:** {top_intent}\n"
                    for key, value in extracted_entities.items():
                        response += f"🔹 **{key}:** {value}\n"

                st.session_state.messages.append({"role": "assistant", "text": response})
                st.rerun()
        
        st.write("### Respuesta del Modelo")
        if st.session_state.messages:
            st.markdown(st.session_state.messages[-1]["text"])
        
        if st.button("🔄 Refrescar Conversación"):
            st.session_state.messages = []
            st.rerun()

if __name__ == "__main__":
    main()
