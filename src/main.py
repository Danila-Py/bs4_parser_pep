import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    BASE_DIR, DOWNLOADS_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP_URL
)
from exceptions import BlockError
from outputs import control_output
from utils import find_tag, get_soup


COMMAND_LINE_ARGUMENTS = 'Аргументы командной строки: {mode} {output}'
DOWNLOAD_MESSAGE = 'Архив был загружен и сохранен: {}'
FIND_BLOCK_ERROR = 'Не найден блок "All versions"'
END_PARSER = 'Парсер завершил работу.'
START_PARSER = 'Парсер запущен!'
ERROR_PARSER = 'Ошибка при работе парсера в режиме: {mode} - {error}'
SOUP_ERROR = 'Ошибка получения soup для {link} - {error}'
ERROR_EXPECTED_STATUS = (
    'Несовпадающие статусы \n'
    '{link} \n'
    '"Статус в карточке:", {status} \n'
    '"Ожидаемые статусы:", \n'
    '{expected}'
)


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    fail_soups = []
    for link in tqdm(soup.select('div.toctree-wrapper li.toctree-l1 > a')):
        version_link = urljoin(whats_new_url, link['href'])
        try:
            soup = get_soup(session, version_link)
            results.append((
                version_link,
                find_tag(soup, 'h1').text,
                find_tag(soup, 'dl').text.replace('\n', ' ')
            ))
        except ConnectionError as error:
            fail_soups.append(SOUP_ERROR.format(link=version_link, error=error))
            continue
    list(map(logging.info, fail_soups))
    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    ul_tags = soup.select('div.sphinxsidebarwrapper ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise BlockError(FIND_BLOCK_ERROR)
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d+\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        text_match = re.match(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append((a_tag['href'], version, status))
    return results


def download(session):
    download_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = get_soup(session, download_url)
    table = find_tag(soup, 'table')
    pdf_a4_tag = find_tag(
        table, 'a', attrs={'href': re.compile(r'.+\.zip$')}
    )
    pdf_url = urljoin(download_url, pdf_a4_tag['href'])
    filename = pdf_url.split('/')[-1]
    download_dir = BASE_DIR / DOWNLOADS_DIR
    download_dir.mkdir(exist_ok=True)
    archive_path = download_dir / filename
    response = session.get(pdf_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(DOWNLOAD_MESSAGE.format(archive_path))


def pep(session):
    all_pep_url = urljoin(PEP_URL, 'numerical/')
    soup = get_soup(session, all_pep_url)
    pep_body = soup.select('tbody tr')
    status_counter = defaultdict(int)
    fail_statuses = []
    for pep in tqdm(pep_body):
        statuses = find_tag(pep, 'abbr')
        hrefs = find_tag(pep, 'a')
        status_of_peps = statuses.text[1:]
        links_to_pep = urljoin(PEP_URL, hrefs['href'])
        try:
            soup = get_soup(session, links_to_pep)
        except ConnectionError as error:
            fail_statuses.append(
                SOUP_ERROR.format(link=links_to_pep, error=error)
            )
        table = find_tag(
            soup, 'dl', attrs={'class': 'rfc2822 field-list simple'}
        )

        status_on_page = None
        for dt in table.find_all('dt'):
            if 'Status' in dt.get_text():
                dd = dt.find_next_sibling('dd')
                status_on_page = dd.get_text()
                break

        status_counter[status_on_page] += 1

        if status_on_page not in EXPECTED_STATUS.get(status_of_peps, ()):
            fail_statuses.append(
                ERROR_EXPECTED_STATUS.format(
                    link=links_to_pep,
                    status=status_on_page,
                    expected=EXPECTED_STATUS.get(status_of_peps, ())
                )
            )
    list(map(logging.info, fail_statuses))

    return [
        ('Статус', 'Количество'),
        *status_counter.items(),
        ('Всего', sum(status_counter.values())),
    ]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info(START_PARSER)
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(COMMAND_LINE_ARGUMENTS.format(**vars(args)))
    try:
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
    except Exception as error:
        logging.info(ERROR_PARSER.format(mode=args.mode, error=error))
    logging.info(END_PARSER)


if __name__ == '__main__':
    main()
