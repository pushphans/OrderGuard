import logging

from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential
from tenacity import before_sleep_log

from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import InterfaceError


TRANSIENT_DB_ERRORS = (OperationalError, InterfaceError)


logger = logging.getLogger("orderguard.retry")


def db_retry(func):
    return retry(
        retry=retry_if_exception_type(TRANSIENT_DB_ERRORS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )(func)
