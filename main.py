from typing import List, Optional
import strawberry
from fastapi import FastAPI, Request, Response
from strawberry.fastapi import GraphQLRouter
from supabase import create_client, Client
from strawberry.schema.config import StrawberryConfig
from PIL import Image
from utils.draw_card import draw_card, digital_code
from dotenv import load_dotenv
import os
import io
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ORIGINS = os.getenv("ORIGINS")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@strawberry.type
class BusinessCard:
    id: Optional[int]
    email: str
    job_title: str
    full_name: str
    phone_number: str
    website: str
    image_url: Optional[str]
    user_id: str
    base_card: str


@strawberry.type
class DigitalCard:
    id: Optional[int]
    email: str
    job_title: str
    full_name: str
    phone_number: str
    website: str
    user_id: str
    slug: str
    qr_code: str
    profile_pic: str


@strawberry.type
class DeleteSuccess:
    message: str


@strawberry.type
class UpdateBusinessCardSuccess:
    business_card: BusinessCard


@strawberry.type
class UpdateDigitalCardSuccess:
    digital_card: DigitalCard


@strawberry.type
class NotFoundError:
    message: str = "Business card not found"


@strawberry.type
class NotAuthorizedError:
    message: str = "Not authorized"


@strawberry.type
class DuplicateCardError:
    message: str = "That card already exists"


UpdateResponse = strawberry.union(
    "UpdateResponse", [UpdateBusinessCardSuccess, NotFoundError, NotAuthorizedError]
)
DeleteResponse = strawberry.union(
    "DeleteResponse", [DeleteSuccess, NotFoundError, NotAuthorizedError]
)
UpdateDigitalResponse = strawberry.union(
    "UpdateDigitalResponse", [UpdateDigitalCardSuccess, NotFoundError, NotAuthorizedError]
)
DigitalCardResponse = strawberry.union(
    "DigitalCardResponse", [DigitalCard, NotFoundError]
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
            auth = supabase.auth.get_user(token)
            request.state.user_id = auth.user.id
            supabase.postgrest.auth(token)
        except Exception:
            return Response("Invalid user token", status_code=401)
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
    @strawberry.field
    async def digital_cards(self, info, slug: str) -> DigitalCardResponse:
        try:
            card = (
                supabase.table("digital_cards")
                .select("*")
                .eq("slug", slug)
                .execute()
            )
            if card.data[0]:
                return DigitalCard(**card.data[0])
            else:
                return NotFoundError()
        except Exception:
            return NotFoundError()

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

    @strawberry.field
    async def digital_cards(self, info) -> List[DigitalCard]:
        user_id = info.context["request"].state.user_id
        try:
            result = (
                supabase.table("digital_cards")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return [DigitalCard(**card) for card in result.data]

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
        website: str,
        base_card: str,
    ) -> BusinessCard:
        user_id = info.context["request"].state.user_id
        check_duplicate = (
            supabase.table("business_cards")
            .select("*")
            .eq("email", email)
            .eq("job_title", job_title)
            .eq("full_name", full_name)
            .eq("phone_number", phone_number)
            .eq("website", website)
            .eq("base_card", base_card)
            .execute()
        )
        if check_duplicate.data:
            return DuplicateCardError()

        # if it doesnt already exist make one
        if check_duplicate.data == []:
            new_card = {
                "email": email,
                "job_title": job_title,
                "full_name": full_name,
                "phone_number": phone_number,
                "website": website,
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
                base_image,
                base_card,
                full_name,
                job_title,
                email,
                phone_number,
                website,
            )

            # Upload the modified image to Supabase storage
            supabase.storage.from_("business_card_images").upload(
                f"{id}.png", img_io.getvalue()
            )
            image_url = (
                f"{SUPABASE_URL}/storage/v1/object/public/business_card_images/{id}.png"
            )

            return BusinessCard(**table_with_img.data[0])

    @strawberry.mutation
    async def update_business_card(
        self,
        info,
        id: int,
        email: Optional[str] = None,
        job_title: Optional[str] = None,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        website: Optional[str] = None,
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
            filename = result.data[0]["image_url"].rsplit("/", 1)[-1]
            supabase.storage.from_("business_card_images").remove(filename)

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
                "website": website
                if website is not None
                else result.data[0]["website"],
                "user_id": user_id,
                "image_url": "placeholder",
                "base_card": base_card
                if base_card is not None
                else result.data[0]["base_card"],
            }

            # Insert the new card into the database
            new_card = supabase.table("business_cards").insert(new_card_data).execute()
            new_id = new_card.data[0]["id"]

            # Load the base business card image
            response = supabase.storage.from_("default_cards").download(base_card)
            img_io = io.BytesIO(response)
            base_image = Image.open(img_io)

            # Draw the new card
            img_io = draw_card(
                base_image,
                base_card,
                new_card_data["full_name"],
                new_card_data["job_title"],
                new_card_data["email"],
                new_card_data["phone_number"],
                new_card_data["website"],
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
            return DeleteSuccess(message=f"Deleted card {id}")

    @strawberry.mutation
    async def create_digital_card(
        self,
        info,
        email: str,
        job_title: str,
        full_name: str,
        phone_number: str,
        website: str,
        profile_pic: str,
        slug: str,
    ) -> DigitalCard:
        user_id = info.context["request"].state.user_id
        complete_slug = "https://business-card-frontend.vercel.app/cards/" + slug
        new_card = {
            "email": email,
            "job_title": job_title,
            "full_name": full_name,
            "phone_number": phone_number,
            "website": website,
            "user_id": user_id,
            "profile_pic": profile_pic,
            "slug": slug,
            "qr_code": "placeholder",
        }
        table_no_code = supabase.table("digital_cards").insert(new_card).execute()
        id = table_no_code.data[0]["id"]
        code = digital_code(complete_slug)
        supabase.storage.from_("digital_card_codes").upload(
            f"{id}.png", code.getvalue()
        )
        code_url = (
            f"{SUPABASE_URL}/storage/v1/object/public/digital_card_codes/{id}.png"
        )
        table_with_code = (
            supabase.table("digital_cards")
            .update({"qr_code": code_url})
            .match({"id": id})
            .execute()
        )
        return DigitalCard(**table_with_code.data[0])

    @strawberry.mutation
    async def update_digital_card(
        self,
        info,
        id: int,
        email: Optional[str] = None,
        job_title: Optional[str] = None,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        website: Optional[str] = None,
        profile_pic: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> UpdateDigitalResponse:
        user_id = info.context["request"].state.user_id
        # Check if the card exists and belongs to the current user
        result = supabase.table("digital_cards").select("*").eq("id", id).execute()
        if not result.data:
            return NotFoundError()
        elif result.data[0]["user_id"] != user_id:
            return NotAuthorizedError(
                message="Not authorized to update this digital card"
            )
        else:
            slug_changed = slug is not None and slug != result.data[0]["slug"]

            if slug_changed:
                # Delete the old qr_code
                filename = result.data[0]["qr_code"].rsplit("/", 1)[-1]
                supabase.storage.from_("digital_card_codes").remove(filename)

            # Prepare the new card data
            print(result.data[0])
            print("profile pic= ",profile_pic)
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
                "website": website
                if website is not None
                else result.data[0]["website"],
                "profile_pic": profile_pic if profile_pic is not None else result.data[0]["profile_pic"],
                "user_id": user_id,
                "slug": slug if slug is not None else result.data[0]["slug"],
                "qr_code": "placeholder" if slug_changed else result.data[0]["qr_code"],
            }

            # Update the card in the database
            new_card = (
                supabase.table("digital_cards")
                .update(new_card_data)
                .eq("id", id)
                .execute()
            )

            if slug_changed:
                # Generate the new qr_code
                code = digital_code(new_card_data["slug"])
                supabase.storage.from_("digital_card_codes").upload(
                    f"{id}.png", code.getvalue()
                )
                code_url = f"{SUPABASE_URL}/storage/v1/object/public/digital_card_codes/{id}.png"
                new_card = supabase.table("digital_cards").update({"qr_code": code_url}).eq(
                    "id", id
                ).execute()

            return UpdateDigitalCardSuccess(
                digital_card=DigitalCard(**new_card.data[0])
            )

    @strawberry.mutation
    async def delete_digital_card(self, info, id: int) -> DeleteResponse:
        user_id = info.context["request"].state.user_id
        # Check if the card exists and belongs to the current user
        result = supabase.table("digital_cards").select("*").eq("id", id).execute()
        if not result.data:
            return NotFoundError()
        elif result.data[0]["user_id"] != user_id:
            return NotAuthorizedError(
                message="Not authorized to delete this digital card"
            )
        else:
            # Delete the qr_code from the bucket
            filename = result.data[0]["qr_code"].rsplit("/", 1)[-1]
            supabase.storage.from_(f"digital_card_codes").remove(filename)
            # Delete the entry from the table
            supabase.table("digital_cards").delete().eq("id", id).execute()
            return DeleteSuccess(message=f"Deleted digital card {id}")


authenticated_schema = strawberry.Schema(
    query=Query, mutation=Mutation, config=StrawberryConfig(auto_camel_case=False)
)
public_schema = strawberry.Schema(query=PublicQuery)
app.include_router(GraphQLRouter(schema=authenticated_schema), prefix="/graphql")
app.include_router(GraphQLRouter(schema=public_schema), prefix="/publicgraphql")
