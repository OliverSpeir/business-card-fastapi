import io
import qrcode
from PIL import ImageDraw, ImageFont


def generate_qr_code(
    website,
    box_size=10,
    border=2,
    fill_color="black",
    back_color="#CCCCCC",
    image_size=(300, 300),
):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(website)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=fill_color, back_color=back_color)
    qr_img_resized = qr_img.resize(image_size)

    return qr_img_resized


def clear_card(image, color):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    left_rectangle = [(0, 0), (450, height)]
    draw.rectangle(left_rectangle, fill=color)
    right_rectangle = [(width - 425, 0), (width, height)]
    draw.rectangle(right_rectangle, fill=color)
    return image


def draw_card(
    base_image, base_card, full_name, job_title, email, phone_number, website
):
    if base_card == "BusinessCard.png":
        print("drawing default card")
        draw = ImageDraw.Draw(base_image)
        font = ImageFont.truetype("./utils/ARIBL0.ttf", 15)
        draw.text((10, 10), f"Full Name: {full_name}", fill="black", font=font)
        draw.text((10, 30), f"Job Title: {job_title}", fill="black", font=font)

        draw.text((10, 50), f"Email: {email}", fill="black", font=font)
        draw.text((10, 70), f"Phone Number: {phone_number}", fill="black", font=font)
        draw.text((10, 90), f"Website: {website}", fill="black", font=font)

        # qr code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(website)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img_resized = qr_img.resize((150, 150))

        # add qr to base image
        base_image.paste(
            qr_img_resized, (base_image.width - qr_img_resized.width - 10, 10)
        )  # paste qr code on the right side of the image

        # format the new picture
        img_io = io.BytesIO()
        base_image.save(img_io, "PNG")
        img_io.seek(0)
        return img_io
    if base_card == "Business-Card-1.png":
        blank_card = clear_card(base_image, "#CCCCCC")
        draw = ImageDraw.Draw(blank_card)
        font_name = ImageFont.truetype("./utils/ARIBL0.ttf", 52)
        font = ImageFont.truetype("./utils/ARIBL0.ttf", 32)
        qr_code = generate_qr_code(website)
        blank_card.paste(qr_code, (blank_card.width - qr_code.width - 670, 75))
        draw.text((80, 400), f"{full_name}", fill="black", font=font_name)
        draw.text((100, 480), f"{job_title}", fill="black", font=font)
        draw.text((640, 140), f"{phone_number}", fill="black", font=font)
        draw.text((640, 270), f"{email}", fill="black", font=font)
        draw.text((640, 410), f"{website}", fill="black", font=font)
        img_io = io.BytesIO()
        blank_card.save(img_io, "PNG")
        img_io.seek(0)
        return img_io
