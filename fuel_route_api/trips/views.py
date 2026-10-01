import json
from pathlib import Path
from urllib.parse import urlencode

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from .clients import ExternalServiceError, InvalidInput, LocationNotFound
from .maphtml import render_map
from .optimizer import NoFeasiblePlan
from .service import plan_trip


_INDEX_HTML = (Path(__file__).parent / "frontend" / "index.html").read_text(encoding="utf-8")


def index_view(request):
    return HttpResponse(_INDEX_HTML)


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


@require_http_methods(["GET", "POST"])
def route_view(request):
    """GET /api/route/?start=Dallas, TX&finish=Denver, CO   (or POST JSON {"start","finish"})
    Optional: format=html -> interactive map page, geojson=1 -> include GeoJSON geometry."""
    if request.method == "POST":
        try:
            params = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return _error("Invalid JSON body.", 400)
    else:
        params = request.GET

    start = str(params.get("start") or "").strip()
    finish = str(params.get("finish") or "").strip()
    if not start or not finish:
        return _error("Both 'start' and 'finish' are required (address or 'lat,lon').", 400)

    try:
        result = plan_trip(start, finish)
    except InvalidInput as exc:
        return _error(str(exc), 400)
    except LocationNotFound as exc:
        return _error(str(exc), 404)
    except NoFeasiblePlan as exc:
        return _error(str(exc), 422)
    except ExternalServiceError as exc:
        return _error(str(exc), 502)

    if str(params.get("format", "")).lower() == "html":
        return HttpResponse(render_map(result))

    geometry = result.pop("_geometry")
    if str(params.get("geojson", "")).lower() in {"1", "true", "yes"}:
        result["route"]["geojson"] = {"type": "LineString", "coordinates": geometry}
    result["map_url"] = request.build_absolute_uri("/api/route/") + "?" + urlencode(
        {"start": start, "finish": finish, "format": "html"}
    )
    return JsonResponse(result)
