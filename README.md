<H2>100% of this Python code was created by GenAI</H2>

Update - 12-Feb-2025. Refactored to Flask from Streamlit. 100% of changes were done using GenAI, no code was hand written. 

This app uses a local deployment of EasyOCR, Ollama and the LLM Aya 23 from Cohere to translate text in images. You provide an image and it translates the text and then generates a new version of the image with the translation overlayed.

I did many (many) prompts and prompt refinements, but did not manually enter a single character of Python code.

Example of a prompt used to refine the code:

<<<<<<<<<<>>>>>>>>>

This python app works great but I need some changes to the overlayed text in the new images.

Please do all of the following:
•	Center the translated text
•	Reduce the size of the box by 10%
•	Make the white box 50% translucent

Please regenerate the full python script.

``` python
(full code goes here)
```
<<<<<<<<<<>>>>>>>>>

![Screenshot_10-2-2025_14359_localhost](https://github.com/user-attachments/assets/91bc29b5-a9e2-42ab-b95a-e361a9288577)

