import io
from PIL import ImageDraw, ImageFont


def draw_card(base_image, full_name, job_title, email, phone_number, linkedin):
    draw = ImageDraw.Draw(base_image)
    font = ImageFont.truetype("./utils/ARIBL0.ttf", 15)
    draw.text((10, 10), f"Full Name: {full_name}", fill="black", font=font)
    draw.text((10, 30), f"Job Title: {job_title}", fill="black", font=font)
    draw.text((10, 50), f"Email: {email}", fill="black", font=font)
    draw.text((10, 70), f"Phone Number: {phone_number}", fill="black", font=font)
    draw.text((10, 90), f"LinkedIn: {linkedin}", fill="black", font=font)

    img_io = io.BytesIO()
    base_image.save(img_io, "PNG")
    img_io.seek(0)
    return img_io
