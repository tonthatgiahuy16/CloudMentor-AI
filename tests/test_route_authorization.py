from fastapi.routing import APIRoute

from app.main import app


PUBLIC = "public"
AUTHENTICATED = "authenticated"
ADMIN = "admin"


# Every application route must be listed here. Adding a route without
# deciding its access policy fails the inventory test.
EXPECTED_POLICY = {
    ("GET", "/"): PUBLIC,
    ("GET", "/healthz"): PUBLIC,
    ("GET", "/readyz"): PUBLIC,
    ("POST", "/auth/token"): PUBLIC,
    ("POST", "/internal/demo-seed"): PUBLIC,
    ("GET", "/subjects/"): AUTHENTICATED,
    ("POST", "/chat/"): AUTHENTICATED,
    ("GET", "/quizzes/"): AUTHENTICATED,
    ("GET", "/quizzes/{quiz_id}"): AUTHENTICATED,
    ("POST", "/quizzes/{quiz_id}/attempts"): AUTHENTICATED,
    ("GET", "/quizzes/attempts/{attempt_id}"): AUTHENTICATED,
    (
        "POST",
        "/quizzes/attempts/{attempt_id}/submit",
    ): AUTHENTICATED,
    ("GET", "/subjects/trash"): ADMIN,
    ("POST", "/subjects/"): ADMIN,
    ("DELETE", "/subjects/{subject_id}"): ADMIN,
    ("POST", "/subjects/{subject_id}/restore"): ADMIN,
    ("POST", "/upload/"): ADMIN,
    ("GET", "/documents/"): ADMIN,
    ("GET", "/documents/{document_id}"): ADMIN,
    ("DELETE", "/documents/{document_id}"): ADMIN,
    (
        "POST",
        "/documents/{document_id}/activate",
    ): ADMIN,
    ("POST", "/quizzes/"): ADMIN,
    ("POST", "/quizzes/{quiz_id}/questions"): ADMIN,
    ("POST", "/quizzes/{quiz_id}/publish"): ADMIN,
    ("GET", "/quizzes/{quiz_id}/overview"): ADMIN,
    ("GET", "/quizzes/{quiz_id}/attempts"): ADMIN,
    ("GET", "/metrics/pipeline"): ADMIN,
}


def _dependency_names(dependant) -> set[str]:
    names = set()

    for dependency in dependant.dependencies:
        if dependency.call is not None:
            names.add(
                getattr(
                    dependency.call,
                    "__name__",
                    type(dependency.call).__name__,
                )
            )
        names |= _dependency_names(dependency)

    return names


def _iter_api_routes(routes):
    """Yield APIRoute objects, descending into included routers.

    FastAPI 0.142 stores ``include_router`` results as an
    ``_IncludedRouter`` wrapper instead of flattening routes into
    ``app.routes``. The wrapper keeps the original router so the real
    APIRoute objects, including their dependencies, stay inspectable.
    """

    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue

        original_router = getattr(
            route,
            "original_router",
            None,
        )
        if original_router is not None:
            yield from _iter_api_routes(
                original_router.routes
            )


def _application_routes():
    routes = []

    for route in _iter_api_routes(app.routes):
        methods = {
            method
            for method in route.methods
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        }

        for method in methods:
            routes.append((method, route.path, route))

    return routes


def test_route_inventory_matches_declared_policy():
    actual = {
        (method, path)
        for method, path, _ in _application_routes()
    }

    assert actual == set(EXPECTED_POLICY)


def test_every_admin_route_depends_on_require_admin():
    violations = []

    for method, path, route in _application_routes():
        policy = EXPECTED_POLICY.get((method, path))
        names = _dependency_names(route.dependant)

        if policy == ADMIN and "require_admin" not in names:
            violations.append((method, path, names))

    assert violations == []


def test_every_authenticated_route_requires_authentication():
    violations = []

    for method, path, route in _application_routes():
        policy = EXPECTED_POLICY.get((method, path))
        names = _dependency_names(route.dependant)

        if policy in {ADMIN, AUTHENTICATED} and not (
            "require_admin" in names
            or "require_authenticated" in names
            or "get_current_user" in names
        ):
            violations.append((method, path, names))

    assert violations == []


def test_public_routes_do_not_depend_on_authentication():
    violations = []

    for method, path, route in _application_routes():
        policy = EXPECTED_POLICY.get((method, path))
        names = _dependency_names(route.dependant)

        if policy == PUBLIC and names & {
            "require_admin",
            "require_authenticated",
            "get_current_user",
        }:
            violations.append((method, path, names))

    assert violations == []


def test_inventory_covers_both_read_and_write_routes():
    methods = {
        method
        for method, _, _ in _application_routes()
    }

    assert "GET" in methods
    assert "POST" in methods
    assert "DELETE" in methods

    # Admin-only GET routes must be protected too; a list endpoint for
    # every employee's results is not a harmless read.
    admin_gets = {
        (method, path)
        for method, path in EXPECTED_POLICY
        if method == "GET"
        and EXPECTED_POLICY[(method, path)] == ADMIN
    }

    assert ("GET", "/quizzes/{quiz_id}/attempts") in admin_gets
    assert ("GET", "/quizzes/{quiz_id}/overview") in admin_gets
    assert ("GET", "/documents/") in admin_gets
