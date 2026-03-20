"""API routers."""

from app.routers.narratives import router as narratives_router
from app.routers.upload import router as upload_router
from app.routers.search import router as search_router
from app.routers.stats import router as stats_router
from app.routers.queue import router as queue_router

narratives = narratives_router
upload = upload_router
search = search_router
stats = stats_router
queue = queue_router

try:
    from app.routers.auth import router as auth_router
    from app.routers.narrators import router as narrators_router
    auth = auth_router
    narrators = narrators_router
except ImportError:
    auth = None
    narrators = None
