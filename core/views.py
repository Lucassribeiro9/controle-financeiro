""" Views do app core. """
from django.http import HttpResponse


def health_check(request):
    return HttpResponse("OK")
