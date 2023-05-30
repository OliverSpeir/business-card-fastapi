from typing import List, Optional
import strawberry
from fastapi import FastAPI, Request, HTTPException, Response
from strawberry.fastapi import GraphQLRouter
from supabase import create_client, Client
from strawberry.schema.config import StrawberryConfig
from PIL import Image
from utils.draw_card import draw_card
from dotenv import load_dotenv
import os
import io
from fastapi.middleware.cors import CORSMiddleware
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
    image_url: Optional[str]
    user_id: str
    base_card: str


@strawberry.type
class DeleteBusinessCardSuccess:
    message: str


@strawberry.type
class UpdateBusinessCardSuccess:
    business_card: BusinessCard


@strawberry.type
class NotFoundError:
    message: str = "Business card not found"


@strawberry.type
class NotAuthorizedError:
    message: str = "Not authorized"


UpdateResponse = strawberry.union(
    "UpdateResponse", [UpdateBusinessCardSuccess, NotFoundError, NotAuthorizedError]
)
DeleteResponse = strawberry.union(
    "DeleteResponse", [DeleteBusinessCardSuccess, NotFoundError, NotAuthorizedError]
)


@app.middleware("http")
async def add_authentication(request: Request, call_next):
    if request.url.path.startswith("/graphql"):
        if request.method == "OPTIONS":
            return await call_next(request)
        
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        if not token:
            return Response("Unauthorized", status_code=401)

        try:
            data = supabase.auth.get_user(token)
        except Exception as e:
            return Response("Invalid user token", status_code=401)

        request.state.user_id = data.user.id
        response = await call_next(request)
        return response
    return await call_next(request)

@strawberry.type
class PublicQuery:
    @strawberry.field
    async def default_card_images(self, info) -> List[str]:
        try:
            result = supabase.storage.from_("default_cards").list()
            if result:
                return [
                    f"{SUPABASE_URL}/storage/v1/object/public/default_cards/{file['name']}"
                    for file in result
                ]

            return []

        except Exception:
            return []

@strawberry.type
class Query:
    @strawberry.field
    async def business_cards(self, info) -> List[BusinessCard]:
        user_id = info.context["request"].state.user_id
        try:
            result = (
                supabase.table("business_cards")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return [BusinessCard(**card) for card in result.data]

        except Exception:
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
        base_card: str,
    ) -> BusinessCard:
        # check if card already exists
        check_duplicate = (
            supabase.table("business_cards")
            .select("*")
            .eq("email", email)
            .eq("job_title", job_title)
            .eq("full_name", full_name)
            .eq("phone_number", phone_number)
            .eq("linkedin", linkedin)
            .execute()
        )
        # if it doesnt already exist make one
        if check_duplicate.data == []:
            user_id = info.context["request"].state.user_id
            new_card = {
                "email": email,
                "job_title": job_title,
                "full_name": full_name,
                "phone_number": phone_number,
                "linkedin": linkedin,
                "user_id": user_id,
                "image_url": "placeholder",
                "base_card": base_card,
            }

            # insert into db with placeholder image_url so we can get the correct id for the image
            table_no_img = supabase.table("business_cards").insert(new_card).execute()
            id = table_no_img.data[0]["id"]

            # Now we know the id, we can generate the actual image_url
            image_url = (
                f"{SUPABASE_URL}/storage/v1/object/public/business_card_images/{id}.png"
            )

            # Update the record with the actual image_url
            table_with_img = (
                supabase.table("business_cards")
                .update({"image_url": image_url})
                .match({"id": id})
                .execute()
            )

            # Load the base business card image
            response = supabase.storage.from_("default_cards").download(base_card)
            img_io = io.BytesIO(response)
            base_image = Image.open(img_io)

            # Draw the new card
            img_io = draw_card(
                base_image, full_name, job_title, email, phone_number, linkedin
            )

            # Upload the modified image to Supabase storage
            path = f"{id}.png"
            supabase.storage.from_("business_card_images").upload(
                path, img_io.getvalue()
            )

            return BusinessCard(**table_with_img.data[0])
        # if duplicate exists return it
        if check_duplicate.data != []:
            return BusinessCard(**check_duplicate.data[0])

    @strawberry.mutation
    async def update_business_card(
        self,
        info,
        id: int,
        email: Optional[str] = None,
        job_title: Optional[str] = None,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        linkedin: Optional[str] = None,
        base_card: Optional[str] = None,
    ) -> UpdateResponse:
        user_id = info.context["request"].state.user_id
        # Check if the card exists and belongs to the current user
        result = supabase.table("business_cards").select("*").eq("id", id).execute()
        if not result.data:
            return NotFoundError()
        elif result.data[0]["user_id"] != user_id:
            return NotAuthorizedError(
                message="Not authorized to update this business card"
            )
        else:
            # Delete the card
            supabase.table("business_cards").delete().eq("id", id).execute()

            # Remove the current image from the bucket
            folder_and_filename = "/".join(
                result.data[0]["image_url"].rsplit("/", 2)[-2:]
            )
            supabase.storage.from_("business_card_images").remove(folder_and_filename)

            # Prepare the new card data
            new_card_data = {
                "email": email if email is not None else result.data[0]["email"],
                "job_title": job_title
                if job_title is not None
                else result.data[0]["job_title"],
                "full_name": full_name
                if full_name is not None
                else result.data[0]["full_name"],
                "phone_number": phone_number
                if phone_number is not None
                else result.data[0]["phone_number"],
                "linkedin": linkedin
                if linkedin is not None
                else result.data[0]["linkedin"],
                "user_id": user_id,
                "image_url": "placeholder",
                "base_card": base_card
                if base_card is not None
                else result.data[0]["base_card"],
            }

            # Insert the new card into the database
            new_card = supabase.table("business_cards").insert(new_card_data).execute()
            new_id = new_card.data[0]["id"]

            # Generate a new image and upload it to the bucket
            # Load the base business card image
            response = supabase.storage.from_("default_cards").download(base_card)
            img_io = io.BytesIO(response)
            base_image = Image.open(img_io)

            # Draw the new card
            img_io = draw_card(
                base_image,
                new_card_data["full_name"],
                new_card_data["job_title"],
                new_card_data["email"],
                new_card_data["phone_number"],
                new_card_data["linkedin"],
            )

            # Upload the modified image to Supabase storage
            path = f"{new_id}.png"
            supabase.storage.from_("business_card_images").upload(
                path, img_io.getvalue()
            )

            # Update the image_url in the new_card_data
            image_url = f"{SUPABASE_URL}/storage/v1/object/public/business_card_images/{new_id}.png"
            supabase.table("business_cards").update({"image_url": image_url}).eq(
                "id", new_id
            ).execute()

            # Return the new business card
            return UpdateBusinessCardSuccess(
                business_card=BusinessCard(**new_card.data[0])
            )

    @strawberry.mutation
    async def delete_business_card(self, info, id: int) -> DeleteResponse:
        user_id = info.context["request"].state.user_id
        # Check if the card exists and belongs to the current user
        result = supabase.table("business_cards").select("*").eq("id", id).execute()
        if not result.data:
            return NotFoundError()
        elif result.data[0]["user_id"] != user_id:
            return NotAuthorizedError(
                message="Not authorized to delete this business card"
            )
        else:
            # Delete the image from the bucket
            filename = result.data[0]["image_url"].rsplit("/", 1)[-1]
            supabase.storage.from_(f"business_card_images").remove(filename)
            # Delete the entry from the table
            supabase.table("business_cards").delete().eq("id", id).execute()
            return DeleteBusinessCardSuccess(message=f"Deleted card {id}")


authenticated_schema = strawberry.Schema(
    query=Query, mutation=Mutation, config=StrawberryConfig(auto_camel_case=False)
)
public_schema = strawberry.Schema(query=PublicQuery)
app.include_router(GraphQLRouter(schema=authenticated_schema), prefix="/graphql")
app.include_router(GraphQLRouter(schema=public_schema), prefix="/publicgraphql")
