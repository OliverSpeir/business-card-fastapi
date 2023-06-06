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


def get_font_size(text, addition=0):
    font_size = 52
    if len(text) <= 20:
        font_size = 52 + addition
    elif len(text) <= 30:
        font_size = 42 + addition
    elif len(text) <= 40:
        font_size = 32 + addition
    else:
        font_size = 28 + addition
    font = ImageFont.truetype("./utils/ContextLight.ttf", font_size)
    return font


def get_y_position(font):
    font_size = font.size
    if font_size >= 32:
        return int(7)
    elif font_size <= 28:
        return int(10)
    elif font_size >= 42:
        return int(0)


def draw_card(
    base_image, base_card, full_name, job_title, email, phone_number, website
):
    if base_card == "BusinessCard.png":
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
        qr_code = generate_qr_code(website)
        blank_card.paste(qr_code, (blank_card.width - qr_code.width - 670, 75))

        name_font = get_font_size(full_name, 4)
        job_font = get_font_size(job_title, -4)
        phone_font = get_font_size(phone_number, -4)
        email_font = get_font_size(email, -6)
        website_font = get_font_size(website)
        draw.text(
            (
                (blank_card.width - draw.textsize(full_name, font=name_font)[0]) / 2
                - 298,
                400,
            ),
            full_name,
            fill="black",
            font=name_font,
        )
        draw.text(
            (
                (blank_card.width - draw.textsize(job_title, font=job_font)[0]) / 2
                - 303,
                480,
            ),
            job_title,
            fill="black",
            font=job_font,
        )
        draw.text(
            (640, (140 + get_y_position(phone_font))),
            f"{phone_number}",
            fill="black",
            font=phone_font,
        )
        draw.text(
            (640, (275 + get_y_position(email_font))),
            f"{email}",
            fill="black",
            font=email_font,
        )
        draw.text(
            (640, (410 + get_y_position(website_font))),
            f"{website}",
            fill="black",
            font=website_font,
        )

        img_io = io.BytesIO()
        blank_card.save(img_io, "PNG")
        img_io.seek(0)
        return img_io


def digital_code(slug):
    code = generate_qr_code(slug, back_color="white")
    img_io = io.BytesIO()
    code.save(img_io, format="PNG")
    img_io.seek(0)
    return img_io
