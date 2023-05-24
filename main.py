from typing import List, Optional
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from supabase import create_client, Client
from PIL import Image
from utils.draw_card import draw_card
from dotenv import load_dotenv
import os
import io

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@strawberry.type
class BusinessCard:
    id: Optional[int]
    email: str
    job_title: str
    full_name: str
    phone_number: str
    linkedin: str
    style: str
    theme: str
    image_url: Optional[str]


@strawberry.type
class Query:
    @strawberry.field
    async def business_cards(self, info) -> List[BusinessCard]:
        result = await supabase.table("business_cards").select().execute()
        return [BusinessCard(**card) for card in result["data"]]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_business_card(
        self,
        info,
        email: str,
        job_title: str,
        full_name: str,
        phone_number: str,
        linkedin: str,
        style: str,
        theme: str,
    ) -> BusinessCard:
        new_card = {
            "email": email,
            "job_title": job_title,
            "full_name": full_name,
            "phone_number": phone_number,
            "linkedin": linkedin,
            "style": style,
            "theme": theme,
        }
        result = supabase.table("business_cards").insert(new_card).execute()
        id = result.data[0]["id"]
        # Load the base business card image
        response = supabase.storage.from_("default_cards").download("BusinessCard.png")
        img_io = io.BytesIO(response)
        base_image = Image.open(img_io)

        # draw the new card
        img_io = draw_card(
            base_image, full_name, job_title, email, phone_number, linkedin
        )

        # Upload the modified image to Supabase storage
        path = f"business_cards/{id}.png"
        upload_result = supabase.storage.from_("business_card_images").upload(
            path, img_io.getvalue()
        )

        # Add the image URL to the card information
        card_with_url = {
            **result.data[0],
            "image_url": f"{SUPABASE_URL}/storage/v1/object/public/business_card_images/{path}",
        }
        return BusinessCard(**card_with_url)


schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI()
app.include_router(GraphQLRouter(schema=schema), prefix="/graphql")
