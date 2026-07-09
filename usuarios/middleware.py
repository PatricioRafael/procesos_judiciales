import threading

_local = threading.local()


def get_current_request():
    return getattr(_local, "request", None)


def get_client_ip(request):
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class RequestActualMiddleware:
    """Guarda la request en un hilo local para que las señales (que no
    reciben la request) puedan saber quién y desde qué IP se hizo algo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            response = self.get_response(request)
        finally:
            _local.request = None
        return response