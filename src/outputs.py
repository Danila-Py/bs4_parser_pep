import csv
import datetime
import logging

from prettytable import PrettyTable

from constants import (
    BASE_DIR,
    DATETIME_FORMAT,
    FILE_OUTPUT,
    PRETTY_OUTPUT,
    RESULTS_DIR
)

SAVE_FILE = 'Файл с результатами был сохранён: {file_path}'


def default_output(results, **kwargs):
    for row in results:
        print(*row)


def pretty_output(results, **kwargs):
    table = PrettyTable()
    table.field_names = results[0]
    table.aligin = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args=None, **kwargs):
    result_dir = BASE_DIR / RESULTS_DIR
    result_dir.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now = datetime.datetime.now()
    now_formatted = now.strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = result_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as file:
        csv.writer(file, dialect=csv.unix_dialect).writerows(results)
    logging.info(SAVE_FILE.format(file_path=file_path))


OUTPUT = {
    PRETTY_OUTPUT: pretty_output,
    FILE_OUTPUT: file_output,
    None: default_output,
}


def control_output(results, cli_args, **kwargs):
    OUTPUT[cli_args.output](results, cli_args=cli_args, **kwargs)