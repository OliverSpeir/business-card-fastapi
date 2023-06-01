# GraphQL Supabase FastAPI - Serverless

- This is an example project for using these techonologies
- There is an accompanying NextJS frontend
- This API provides CRUD functionality for the business card DB and generates a png image of a new card using Pillow library when card entries are created in the DB

## GraphQL

- Using [Strawberry](https://github.com/strawberry-graphql/strawberry) library which is recommended by FastAPI

## Supabase

- Using [supabase-py](https://github.com/supabase-community/supabase-py) which is recommended by Supabase
- Uses the Storage buckets and Postgres DB offered by Supabase
- Uses Supabase Auth to validate the authenticated requests from frontend

## Serverless Function

- This API is deployed as a Serverless Function on Vercel

### Resources

- [Strawberry FastAPI docs](https://strawberry.rocks/docs/integrations/fastapi)
- [Supabase Python docs](https://supabase.com/docs/reference/python/initializing)
- [Python Imaging Library](https://pypi.org/project/Pillow/)
- [Frontend Repo](https://github.com/OliverSpeir/business-card-frontend)
