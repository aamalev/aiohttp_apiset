from typing import Any, Callable, Optional

from .handler import create_handler
from .parameters.extractor import ParametersExtractor
from .parameters.payload import PayloadReader
from .schema import Parameter, Payload


OperationDecorator = Callable[[Any], Callable]


def operation(
    *parameters: Parameter,
    payload: Optional[Payload] = None,
    payload_reader: Optional[PayloadReader] = None
) -> OperationDecorator:
    # TODO: add openapi specification support
    # we will need to convert parameters and payload to corresponding openapi models and
    # inject the operation to specification

    def decorator(handler: Any) -> Callable:
        return create_handler(handler, ParametersExtractor(
            parameters=list(parameters),
            payload=payload,
            payload_reader=payload_reader
        ))
    return decorator
