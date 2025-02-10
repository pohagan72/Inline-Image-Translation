import streamlit as st
import easyocr
import requests
import json
from PIL import Image, ImageDraw, ImageFont
import io
import os

# Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "aya:latest")

# Function to initialize EasyOCR reader based on selected language
def initialize_reader(target_language):
    language_map = {
        "Chinese": ['ch_sim', 'en'],
        "Arabic": ['ar', 'en'],
        "French": ['fr', 'en'],
        "German": ['de', 'en'],
        "English": ['en']
    }
    return easyocr.Reader(language_map.get(target_language, ['en']))

# Function to send request to Ollama API
def send_ollama_request(prompt):
    try:
        response = requests.post(OLLAMA_API_URL, json={"prompt": prompt, "model": OLLAMA_MODEL}, stream=True)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with Ollama API: {e}")
        return None

# Function to translate a single word using Ollama
def translate_word(word, target_language):
    system_prompt = f"You are an expert in translating individual words to {target_language}. You will be given a single word, and you must return only its direct translation in {target_language}, without any additional context, explanation, or surrounding words. If the word is already in {target_language} or does not need translation, return the word as is."
    user_prompt = f"Translate the following word to {target_language}: {word}"
    prompt = f"{system_prompt}\n\n{user_prompt}"

    response = send_ollama_request(prompt)
    if not response:
        return word  # Return the original word if translation fails

    full_response = ""
    for line in response.iter_lines():
        if line:
            try:
                json_response = line.decode('utf-8')
                data = json.loads(json_response)
                if 'response' in data:
                    full_response += data['response']
                if data.get('done', False):
                    break
            except json.JSONDecodeError:
                print(f"Error decoding JSON: {line}")
                continue
    
    return full_response.strip()

# Function to overlay translated text on the image
def overlay_text_on_image(image, results, target_language):
    draw = ImageDraw.Draw(image)
    
    try:
        # Initial font size, will be adjusted
        font_size = 20
        # --- FIX: Use a font that supports Chinese characters ---
        if target_language == "Chinese":
            font = ImageFont.truetype("msyh.ttc", font_size)  #  Microsoft YaHei
        else:
            font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        st.warning("Default font not found, using a fallback font.  Appearance may differ.") # Better error message
        font = ImageFont.load_default()
        font_size = 10 # Default font size

    for bbox, text, _ in results:
        # Split the detected text into individual words
        words = text.split()
        translated_words = []
        for word in words:
            translation = translate_word(word, target_language)
            translated_words.append(translation)
        
        translated_text = " ".join(translated_words)

        top_left = tuple(map(int, bbox[0]))
        bottom_right = tuple(map(int, bbox[2]))

        # Calculate the height of the original text box
        original_height = bottom_right[1] - top_left[1]
        original_width = bottom_right[0] - top_left[0]

        # Adjust font size based on the height of the original text
        font_size = max(12, int(original_height * 0.8))  # Ensure a minimum font size
        try:
            if target_language == "Chinese":
                font = ImageFont.truetype("msyh.ttc", font_size)
            else:
                font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
            font_size = int(original_height * 0.6)

        # Get the bounding box of the *translated* text
        text_bbox = draw.textbbox(top_left, translated_text, font=font)
        translated_width = text_bbox[2] - text_bbox[0]
        translated_height = text_bbox[3] - text_bbox[1]
        
        # Draw white background box
        bg_top_left = top_left
        bg_bottom_right = (top_left[0] + original_width, top_left[1] + original_height) #fixed size based on original
        draw.rectangle(bg_top_left + bg_bottom_right, fill="white")

        # Draw the translated text in bold red
        draw.text(top_left, translated_text, font=font, fill="red")

    return image

# Streamlit app
st.title("Image Word-by-Word Translation")

# Upload image
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])

# Select target language
target_language = st.selectbox("Select the language to translate into:", ["English", "French", "German", "Chinese", "Arabic"])

# Add a "Translate" button
if st.button("Translate"):
    if uploaded_file is not None and target_language:
        # Initialize the EasyOCR reader based on the selected language
        reader = initialize_reader(target_language)

        # Read the image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)

        # Extract text from the image
        with st.spinner("Extracting text from image..."):
            results = reader.readtext(image)

        # Translate and overlay the text word by word
        with st.spinner("Translating and overlaying text..."):
            translated_image = overlay_text_on_image(image, results, target_language)

        # Display the translated image
        st.image(translated_image, caption="Translated Image (Word-by-Word)", use_container_width=True)

        # Provide a download link for the translated image
        buffered = io.BytesIO()
        translated_image.save(buffered, format="PNG")
        st.download_button(label="Download Translated Image", data=buffered.getvalue(), file_name="translated_image_word_by_word.png", mime="image/png")
    else:
        st.warning("Please upload an image and select a target language before clicking 'Translate'.")
