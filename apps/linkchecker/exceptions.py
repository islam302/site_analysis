"""Domain exceptions for the link checker."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class CrawlJobNotFoundError(ApplicationError):
    default_message = "Crawl job not found."
    default_status = status.HTTP_404_NOT_FOUND


class RobotsDisallowedError(ApplicationError):
    default_message = "Crawling this URL is disallowed by robots.txt."
    default_status = status.HTTP_403_FORBIDDEN
