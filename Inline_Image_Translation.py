from flask import Flask, render_template, request, send_file, jsonify
import easyocr
import requests
import json
from PIL import Image, ImageDraw, ImageFont
import io
import os

app = Flask(__name__)

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
        print(f"Error communicating with Ollama API: {e}")
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
            font = ImageFont.truetype("msyh.ttc", font_size)  # Microsoft YaHei
        else:
            font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        print("Default font not found, using a fallback font.  Appearance may differ.")  # Better error message
        font = ImageFont.load_default()
        font_size = 10  # Default font size

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

        # Adjust the size of the white box to be 25% smaller
        new_width = int(original_width * 0.75)
        new_height = int(original_height * 0.75)

        # Center the white box within the original text box
        bg_top_left = (top_left[0] + (original_width - new_width) // 2, top_left[1] + (original_height - new_height) // 2)
        bg_bottom_right = (bg_top_left[0] + new_width, bg_top_left[1] + new_height)

        # Draw white background box with 25% transparency
        bg_color = (255, 255, 255, 191)  # 25% transparent white
        draw.rectangle(bg_top_left + bg_bottom_right, fill=bg_color)

        # Center the translated text within the white box
        text_position = (
            bg_top_left[0] + (new_width - translated_width) // 2,
            bg_top_left[1] + (new_height - translated_height) // 2
        )

        # Draw the translated text in bold red
        draw.text(text_position, translated_text, font=font, fill="red")

    return image

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get the uploaded file and target language
        uploaded_file = request.files["image"]
        target_language = request.form["language"]

        if uploaded_file and target_language:
            # Initialize the EasyOCR reader based on the selected language
            reader = initialize_reader(target_language)

            # Read the image
            image = Image.open(uploaded_file)

            # Extract text from the image
            results = reader.readtext(image)

            # Translate and overlay the text word by word
            translated_image = overlay_text_on_image(image, results, target_language)

            # Save the translated image to a BytesIO object
            buffered = io.BytesIO()
            translated_image.save(buffered, format="PNG")
            buffered.seek(0)

            # Return the translated image as a downloadable file
            return send_file(buffered, mimetype="image/png", as_attachment=True, download_name="translated_image_word_by_word.png")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)