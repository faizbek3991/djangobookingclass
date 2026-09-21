from .models import SiteSEOSettings


def seo_settings(request):
    return {"site_seo": SiteSEOSettings.get_solo()}
