import json
from pathlib import Path
import streamlit as st
from openai import OpenAI
from dotenv import dotenv_values
import base64

model_pricings = {
    "gpt-4o": {
        "input_tokens": 5.00 / 1_000_000,  # per token
        "output_tokens": 15.00 / 1_000_000,  # per token
    },
    "gpt-4o-mini": {
        "input_tokens": 0.150 / 1_000_000,  # per token
        "output_tokens": 0.600 / 1_000_000,  # per token
    }
}
MODEL = "gpt-4o"
USD_TO_PLN = 3.97
PRICING = model_pricings[MODEL]

# Funkcja do inicjowania klienta OpenAI, przechowująca go w session_state
def init_openai_client():
    if "openai_client" not in st.session_state:
        # Pytanie użytkownika o klucz API, jeśli nie został podany
        api_key = st.text_input("Wprowadź swój klucz OpenAI API:", type="password")
        
        if api_key:
            try:
                # Inicjowanie klienta i przechowywanie go w session_state
                st.session_state.openai_client = OpenAI(api_key=api_key)
                st.success("Klucz API poprawnie zapisany!")
            except Exception as e:
                st.error(f"Wystąpił błąd podczas inicjalizacji klienta OpenAI: {e}")
        else:
            st.warning("Aby kontynuować, wprowadź swój klucz OpenAI API.")
    return st.session_state.get("openai_client")

def img_to_bytes(img_path):
    """Konwertuje obraz na ciąg bajtów zakodowany w Base64."""
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

img_path = "logo.png"

header_html = f"""
    <img src="data:image/png;base64,{img_to_bytes(img_path)}" class="img-fluid" width="100" height="100" style="display: inline-block; vertical-align: middle;">
    <h1 style="display: inline-block; vertical-align: middle; margin-left: 20px;">GPT PIONIERA</h1>
"""

# Wyświetlanie nagłówka za pomocą st.markdown
# Opcja unsafe_allow_html=True jest wymagana do renderowania kodu HTML
st.markdown(header_html, unsafe_allow_html=True)

# Inicjowanie klienta OpenAI (lub pobieranie go z session_state)
openai_client = init_openai_client()

# Warunek, który upewnia się, że klient został poprawnie zainicjowany
if openai_client:
    st.success("Klient OpenAI jest gotowy do użycia.")

def chatbot_reply(user_prompt, memory):
    # dodaj system message
    messages = [
        {
            "role": "system",
            "content": st.session_state["chatbot_personality"],
        },
    ]
    # dodaj wszystkie wiadomości z pamięci
    for message in memory:
        messages.append({"role": message["role"], "content": message["content"]})

    # dodaj wiadomość użytkownika
    messages.append({"role": "user", "content": user_prompt})

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    usage = {}
    if response.usage:
        usage = {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "role": "assistant",
        "content": response.choices[0].message.content,
        "usage": usage,
    }

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("O co chcesz spytać?")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        response = chatbot_reply(prompt, memory=st.session_state["messages"][-10:])
        st.markdown(response["content"])

    st.session_state["messages"].append({"role": "assistant", "content": response["content"], "usage": response["usage"]})

with st.sidebar:
    total_cost = 0
    for message in st.session_state.get("messages") or []:
        if "usage" in message:
            total_cost += message["usage"]["prompt_tokens"] * PRICING["input_tokens"]
            total_cost += message["usage"]["completion_tokens"] * PRICING["output_tokens"]

    c0, c1 = st.columns(2)
    with c0:
        st.metric("Koszt rozmowy (USD)", f"${total_cost:.4f}")

    with c1:
        st.metric("Koszt rozmowy (PLN)", f"{total_cost * USD_TO_PLN:.4f}")

    st.session_state["chatbot_personality"] = st.text_area(
        "Opisz osobowość chatbota",
        max_chars=1000,
        height=200,
        value="""
Jesteś pomocnikiem, który odpowiada na wszystkie pytania użytkownika.
Odpowiadaj na pytania w sposób zwięzły i zrozumiały.
        """.strip()
    )
