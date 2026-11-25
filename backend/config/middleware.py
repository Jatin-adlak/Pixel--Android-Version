def private_api_responses(get_response):
    def middleware(request):
        response = get_response(request)
        if request.path_info.startswith("/api/v1/") and not request.path_info.startswith(
            "/api/v1/media/"
        ):
            response["Cache-Control"] = "no-store"
        return response

    return middleware
