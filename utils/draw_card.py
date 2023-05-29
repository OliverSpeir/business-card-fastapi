import io
import qrcode
from PIL import ImageDraw, ImageFont

def draw_card(base_image, full_name, job_title, email, phone_number, linkedin):
    draw = ImageDraw.Draw(base_image)
    font = ImageFont.truetype("./utils/ARIBL0.ttf", 15)
    draw.text((10, 10), f"Full Name: {full_name}", fill="black", font=font)
    draw.text((10, 30), f"Job Title: {job_title}", fill="black", font=font)
    draw.text((10, 50), f"Email: {email}", fill="black", font=font)
    draw.text((10, 70), f"Phone Number: {phone_number}", fill="black", font=font)
    draw.text((10, 90), f"LinkedIn: {linkedin}", fill="black", font=font)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(linkedin)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_img_resized = qr_img.resize((150, 150))  # adjust size as needed

    base_image.paste(qr_img_resized, (base_image.width - qr_img_resized.width - 10, 10))  # paste qr code on the right side of the image

    img_io = io.BytesIO()
    base_image.save(img_io, "PNG")
    img_io.seek(0)
    return img_io
