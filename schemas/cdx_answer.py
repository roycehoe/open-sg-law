from pydantic import RootModel


class CdxAnswer(RootModel[list[list[str]]]):
    pass
