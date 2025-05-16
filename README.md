# paperal backend

This is supposed to help setup the backend API infrastructure for the [Paperal](https://paperal.com/) application.

The frontend code and the old backend code can be found at the [other repository.](https://github.com/dhruvb26/paperal)

To setup the project, it is recommended to have [`uv`](https://github.com/astral-sh/uv) installed as the Python package and project manager. [`homebrew`](https://brew.sh/) can be used to install `uv`

```
brew install uv
```

Clone this repository and navigate to it

```
git clone https://github.com/dhruvb26/paperal-backend.git

cd paperal-backend
```

Once the package manager is installed, we can go ahead and install the other project dependencies which can be found in two places: the [pyproject.toml](pyproject.toml) file or the [requirements.txt](requirements.txt) file.

Use the command below in the root folder to install the dependencies

```
uv sync
```

Let's install Redis locally if you don't already have it. It is required for the backend store and queue implemented by [Celery](https://docs.celeryq.dev/)

```
brew install redis
```

Then run it locally

```bash
redis-server

redis-cli ping # will return PONG if running
```

## environment

There is an example environment variable file that you should copy as `.env` and populate with the variables. For the `REDIS_URL`, if using [Docker](https://www.docker.com/) the default will be `redis://redis:6379/0` but if running Redis locally it will be `redis://localhost:6379`.

## structure

This repo is responsible for all things backend. The high-level API is implemented through [FastAPI](https://fastapi.tiangolo.com/). There are four main endpoints:

- `/topic` - Given a user query, returns the extracted topic that will also serve as the heading for the paper.

- `/search` - The topic received from the endpoint above is passed to this to initiate a web search for all relevant PDFs on the web.

- `/process` - Once the URLs from search are returned, a Celery task is initiated through this endpoint with all those URLs.

- `/generate` - Given user's previously written content, gives the suggestion.

These four endpoints depend on lots of other packages that are defined in the repository.

The `src` folder at the root is home to all these packages that are made up of smaller modules:

1. `api` - Home to the Celery application and the FastAPI application with a package `routes` that defines the endpoints.

2. `graph` - Responsible for the flow that is initiated when a request hits the `/generate` endpoint.

[main.py](src/graph/main.py) is the agent implementation using [LangGraph](https://langchain-ai.github.io/langgraph/) and [vector_search.py](src/graph/vector_search.py) implements an executable tool to query the vector database.

3. `helpers` - Manages the PostgreSQL instance through [Supabase](https://supabase.com/), vector database through [Pinecone](https://www.pinecone.io/), functions to query [Google Gemini](https://ai.google.dev/) and implementation of search functions for PDFs.

4. `models` - Pretty self-explanatory, has all the models used throughout the application.

5. `utils` - Smaller functions that take care of specific tasks like regex checking, chunking through [LangChain](https://www.langchain.com/) and [Chunkr](https://chunkr.ai/).

6. `sample` - Sample JSON data for chunks.

There is a top-level [run.py](src/run.py) file that launches both the FastAPI and Celery app in parallel. This is also the file run by Docker finally.

**NOTE:** Make sure to launch both services from the `src` folder.

Celery

```
celery -A api.celery_app:celery_app worker --loglevel=info
```

FastAPI

```
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

## deployment

The application itself is dockerized and hosted through [Render](https://render.com/) that takes care of pushing the image to a registry and pulling it to finally set it up.

The dockerfile and the docker compose can be edited if any changes are made in the future.

After cloning the repository, the following command will spin up the containers locally if you have the Docker engine running

```
docker compose up -d
```
