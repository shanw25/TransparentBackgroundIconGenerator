import os
import requests
from openai import OpenAI
from PIL import Image
import shutil
import base64
from io import BytesIO

# Initialize the OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY_DEWAN")
)

def generate_initial_image(object_name, output_path):
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"Create a simple, flat, pure white {object_name} vector icon with pure black background.",
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    image_response = requests.get(image_url)

    if image_response.status_code == 200:
        with open(output_path, "wb") as file:
            file.write(image_response.content)
    else:
        print("Failed to download image")

def binarize_image(input_image_path, output_image_path, size=(100, 100), threshold=128):
    image = Image.open(input_image_path)
    image = image.convert("L")
    binary_image = image.point(lambda p: 255 if p > threshold else 0)
    binary_image = binary_image.convert("RGB")
    binary_image.save(output_image_path)

def png_to_transparent(png_path, output_path):
    image = Image.open(png_path).convert("RGBA")
    data = image.getdata()
    new_data = [(255, 255, 255, 0) if item[0] < 10 and item[1] < 10 and item[2] < 10 else item for item in data]
    image.putdata(new_data)
    image.save(output_path)

def resize_image(input_image_path, output_image_path, size=(50, 50)):
    image = Image.open(input_image_path)
    image = image.resize(size)
    image.save(output_image_path)

def change_background_color(png_path, background_color, output_path):
    image = Image.open(png_path).convert("RGBA")
    new_image = Image.new("RGBA", image.size, background_color)
    new_image.paste(image, (0, 0), image)
    new_image.save(output_path)

def process_images(object_name):
    os.makedirs(f"outputs/{object_name}", exist_ok=True)
    
    initial_image_path = f"outputs/{object_name}/1_initial.png"
    generate_initial_image(object_name, initial_image_path)
    
    grayscale_image_path = f"outputs/{object_name}/2_grayscale.png"
    binarize_image(initial_image_path, grayscale_image_path)
    
    transparent_image_path = f"outputs/{object_name}/3_transparent.png"
    png_to_transparent(grayscale_image_path, transparent_image_path)
    
    resized_image_path = f"outputs/{object_name}/4_resized.png"
    resize_image(transparent_image_path, resized_image_path)
    
    final_image_path = f"outputs/{object_name}/5_final.png"
    change_background_color(resized_image_path, (255, 0, 0, 255), final_image_path)

def modify_icon(object_name, modification_description):
    input_image_path = f"outputs/{object_name}/1_initial.png"
    if not os.path.exists(input_image_path):
        print(f"No existing icon found for {object_name}")
        return
    img_str = image_path_to_ByteIO(input_image_path)
    mask = image_path_to_ByteIO(generate_transparent_image())

    original_prompt = f"The icon is generated using the following prompt: Create a simple, flat, pure white {object_name} vector icon with pure black background."
    full_prompt = f"{original_prompt} Your task is to modify the icon as follows: {modification_description}. Try to modify while making less modification and following the original prompt."

    response = client.images.edit(
        image=img_str,
        mask=mask,
        prompt=full_prompt,
        size="1024x1024",
        n=1,
    )

    image_url = response.data[0].url
    image_response = requests.get(image_url)

    if image_response.status_code == 200:
        version_count = len([name for name in os.listdir("outputs") if name.startswith(object_name)])
        versioned_folder = f"outputs/{object_name}_v{version_count + 1}"
        os.makedirs(versioned_folder, exist_ok=True)
        modified_image_path = f"{versioned_folder}/1_modified_initial.png"
        
        with open(modified_image_path, "wb") as file:
            file.write(image_response.content)
        
        print("Here is the modified image. Do you want to replace the original icon? (yes/no)")
        user_input = input().strip().lower()
        if user_input == "yes":
            shutil.copy(modified_image_path, f"outputs/{object_name}/1_initial.png")
            process_images(object_name)  # Reprocess images after modification
        else:
            print(f"Modified image saved at {modified_image_path}")
            # Process the modified image through the pipeline
            grayscale_image_path = f"{versioned_folder}/2_grayscale.png"
            binarize_image(modified_image_path, grayscale_image_path)
            
            transparent_image_path = f"{versioned_folder}/3_transparent.png"
            png_to_transparent(grayscale_image_path, transparent_image_path)
            
            resized_image_path = f"{versioned_folder}/4_resized.png"
            resize_image(transparent_image_path, resized_image_path)
            
            final_image_path = f"{versioned_folder}/5_final.png"
            change_background_color(resized_image_path, (255, 0, 0, 255), final_image_path)
    else:
        print("Failed to download modified image")

def image_path_to_ByteIO(input_image_path):
    input_image = Image.open(input_image_path)
    if input_image.mode != 'RGBA':
            input_image = input_image.convert('RGBA')
    buffered = BytesIO()
    input_image.save(buffered, format="PNG")
    return buffered.getvalue()

def generate_transparent_image():
    # Create a new image with mode 'RGBA' (to include an alpha channel)
    width, height = 1024, 1024
    transparent_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))  # (0, 0, 0, 0) means fully transparent

    # Save the image to a file
    transparent_image.save("./transparent_image.png", "PNG")

    return "./transparent_image.png"

def main():
    print("Do you want to create a new icon or modify an existing icon? (create/modify)")
    choice = input().strip().lower()
    
    if choice == "create":
        print("Enter the object name:")
        object_name = input().strip()
        process_images(object_name)
        print(f"Generated 5 images for {object_name} and saved them in outputs/{object_name}/")
    elif choice == "modify":
        print("Enter the name of the icon you want to modify:")
        object_name = input().strip()
        print("Enter the description of the modification:")
        modification_description = input().strip()
        modify_icon(object_name, modification_description)
    else:
        print("Invalid choice. Please enter 'create' or 'modify'.")

if __name__ == "__main__":
    main()
