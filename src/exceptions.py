class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""


class BlockError(Exception):
    """Вызывается, когда важный элемент страницы не найден."""