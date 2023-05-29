from typing import List, Optional
import strawberry
from fastapi import FastAPI, Request, HTTPException, Depends, Response
from strawberry.fastapi import GraphQLRouter
from supabase import create_client, Client
from strawberry.schema.config import StrawberryConfig
from PIL import Image
from utils.draw_card import draw_card
from dotenv import load_dotenv
from jose import JWTError, jwt
import os
import io
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware

# from fastapi.middleware.gzip import GZipMiddleware
import logging

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


logging.basicConfig(level=logging.DEBUG)


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
    user_id: str

# @app.middleware("http")
# async def print_request_body(request: Request, call_next):
#     # Get the request body
#     body_bytes = await request.body()
#     body = body_bytes.decode('utf-8')  # Replace 'utf-8' with the appropriate encoding

#     # Print the request body
#     # print("Request Body:", body)

#     # Call the next middleware or endpoint
#     response = await call_next(request)

#     return response


@app.middleware("http")
async def add_authentication(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    if not token:
        return Response("Unauthorized", status_code=401)

    try:
        data = supabase.auth.get_user(token)
    except Exception as e:
        print(e)
        return Response("Invalid user token", status_code=401)

    request.state.user_id = data.user.id
    response = await call_next(request)
    return response


@strawberry.type
class Query:
    @strawberry.field
    async def business_cards(self, info) -> List[BusinessCard]:
        user_id = info.context["request"].state.user_id

        try:
            result = (
                supabase.table("business_cards")
                .select()
                .eq("user_id", user_id)
                .execute()
            )

            return [BusinessCard(**card) for card in result.data]
        except Exception as e:
            print(f"Error retrieving business cards: {str(e)}")
            return []


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
        print("creating  card")
        new_card = {
            "email": email,
            "job_title": job_title,
            "full_name": full_name,
            "phone_number": phone_number,
            "linkedin": linkedin,
            "style": style,
            "theme": theme,
            "user_id": info.context["request"].state.user_id,
            "image_url": "placeholder",
        }

        table_no_img = supabase.table("business_cards").insert(new_card).execute()
        id = table_no_img.data[0]["id"]

        # Now we know the id, we can generate the actual image_url
        image_url = f"{SUPABASE_URL}/storage/v1/object/public/business_card_images/business_cards/{id}.png"

        # Update the record with the actual image_url
        table_with_img = (
            supabase.table("business_cards")
            .update({"image_url": image_url})
            .match({"id": id})
            .execute()
        )

        # Load the base business card image
        response = supabase.storage.from_("default_cards").download("BusinessCard.png")
        img_io = io.BytesIO(response)
        base_image = Image.open(img_io)

        # Draw the new card
        img_io = draw_card(
            base_image, full_name, job_title, email, phone_number, linkedin
        )

        # Upload the modified image to Supabase storage
        path = f"business_cards/{id}.png"
        supabase.storage.from_("business_card_images").upload(path, img_io.getvalue())

        return BusinessCard(**table_with_img.data[0])  # return the image URL string


@strawberry.mutation
async def delete_business_card(self, info, card_id: int):
    user_id = info.context["request"].state.user_id
    # Check if the card exists and belongs to the current user
    result = (
        await supabase.table("business_cards").select().filter("id", card_id).execute()
    )
    if not result["data"]:
        raise HTTPException(status_code=404, detail="Business card not found")
    elif result["data"][0]["user_id"] != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this business card"
        )
    else:
        # Delete the card
        await supabase.table("business_cards").delete().filter("id", card_id).execute()
        return {"message": f"Deleted card {card_id}"}


schema = strawberry.Schema(
    query=Query, mutation=Mutation, config=StrawberryConfig(auto_camel_case=False)
)
app.include_router(GraphQLRouter(schema=schema), prefix="/graphql")
