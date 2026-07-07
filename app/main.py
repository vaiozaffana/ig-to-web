from fastapi import FastAPI
from fastapi.routing import APIRoute, APIRouter

from app.api.v1 import admin, health, publish, webhooks


def include_router(app: FastAPI, router: APIRouter, prefix: str = "") -> None:
    for route in router.routes:
        if not isinstance(route, APIRoute):
            app.router.routes.append(route)
            continue

        app.add_api_route(
            f"{prefix}{route.path}",
            route.endpoint,
            response_model=route.response_model,
            status_code=route.status_code,
            tags=route.tags,
            dependencies=route.dependencies,
            summary=route.summary,
            description=route.description,
            response_description=route.response_description,
            responses=route.responses,
            deprecated=route.deprecated,
            name=f"{prefix.strip('/').replace('/', '_')}_{route.name}" if prefix else route.name,
            methods=list(route.methods or []),
            operation_id=route.operation_id,
            response_model_include=route.response_model_include,
            response_model_exclude=route.response_model_exclude,
            response_model_by_alias=route.response_model_by_alias,
            response_model_exclude_unset=route.response_model_exclude_unset,
            response_model_exclude_defaults=route.response_model_exclude_defaults,
            response_model_exclude_none=route.response_model_exclude_none,
            include_in_schema=route.include_in_schema,
            response_class=route.response_class,
            openapi_extra=route.openapi_extra,
        )


def create_app() -> FastAPI:
    app = FastAPI(title="Instagram Article Automation", version="0.1.0")
    include_router(app, health.router)
    include_router(app, health.router, prefix="/api")
    include_router(app, admin.router)
    include_router(app, admin.router, prefix="/api")
    include_router(app, webhooks.router)
    include_router(app, webhooks.router, prefix="/api")
    include_router(app, publish.router)
    include_router(app, publish.router, prefix="/api")
    return app


app = create_app()
