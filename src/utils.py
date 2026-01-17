from bs4 import BeautifulSoup
from requests import RequestException

from exceptions import ParserFindTagException


REQUEST_ERROR = 'Возникла ошибка при загрузке страницы {url} - {error}'
TAG_ERROR = 'Не найден тег {tag} {attrs}'


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException as error:
        raise ConnectionError(
            REQUEST_ERROR.format(url=url, error=error)
        )


def get_soup(session, url, parser='lxml'):
    return BeautifulSoup(get_response(session, url).text, parser)


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=({} if attrs is None else attrs))
    if searched_tag is None:
        error_message = TAG_ERROR.format(tag=tag, attrs=attrs)
        raise ParserFindTagException(error_message)
    return searched_tag