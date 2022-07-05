from pydantic import BaseModel, Extra


class Model(BaseModel):
    class Config:
        extra: Extra = Extra.allow

        @staticmethod
        def alias_generator(value: str) -> str:
            return _to_camel_case(value)

    def __repr_args__(self):
        return [
            (key, value)
            for key, value in self.__dict__.items()
            if value is not None
        ]


def _to_camel_case(value: str) -> str:
    parts = value.strip('_').split('_')
    parts[1:] = [word.capitalize() for word in parts[1:]]
    return ''.join(parts)
