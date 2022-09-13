from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from ...schema import Schema as BaseSchema
from .base import Model


class ExternalDocumentation(Model):
    """
    Allows referencing an external resource for extended documentation.
    """
    description: Optional[str]
    url: str


class Discriminator(Model):
    """
    When request bodies or response payloads may be one of a number of different schemas,
    a discriminator object can be used to aid in serialization, deserialization, and validation.
    The discriminator is a specific object in a schema which is used to inform the consumer
    of the document of an alternative schema based on the value associated with it.

    When using the discriminator, inline schemas will not be considered.
    """
    property_name: str
    mapping: Optional[Dict[str, str]]


class Xml(Model):
    """
    A metadata object that allows for more fine-tuned XML model definitions.

    When using arrays, XML element names are not inferred (for singular/plural forms)
    and the name property SHOULD be used to add that information. See examples for expected behavior.
    """
    name: Optional[str]
    namespace: Optional[str]
    prefix: Optional[str]
    attribute: Optional[bool]
    wrapped: Optional[bool]


class Schema(BaseSchema):
    """
    JSON Schema: A Media Type for Describing JSON Documents

    https://json-schema.org/draft/2020-12/json-schema-core.html

    The OpenAPI Schema Object dialect for this version of the specification is identified by the
    URI https://spec.openapis.org/oas/3.1/dialect/base (the “OAS dialect schema id”).

    The following properties are taken from the JSON Schema specification
    but their definitions have been extended by the OAS:

    - description - CommonMark syntax MAY be used for rich text representation.
    - format - See Data Type Formats for further details. While relying on JSON Schema’s defined formats,
               the OAS offers a few additional predefined formats.

    In addition to the JSON Schema properties comprising the OAS dialect,
    the Schema Object supports keywords from any other vocabularies, or entirely arbitrary properties.
    """
    discriminator: Optional[Discriminator]
    xml: Optional[Xml]
    external_docs: Optional[ExternalDocumentation]
    example: Optional[Any]


class Reference(Model):
    """
    A simple object to allow referencing other components in the OpenAPI document, internally and externally.

    The $ref string value contains a URI [RFC3986], which identifies the location of the value being referenced.
    https://spec.openapis.org/oas/v3.1.0#bib-RFC3986

    See the rules for resolving Relative References.
    https://spec.openapis.org/oas/v3.1.0#relativeReferencesURI
    """
    ref: str = Field(alias='$ref')
    summary: Optional[str]
    description: Optional[str]


class Example(Model):
    """
    In all cases, the example value is expected to be compatible
    with the type schema of its associated value.

    Tooling implementations MAY choose to validate compatibility automatically,
    and reject the example value(s) if incompatible.
    """
    summary: Optional[str]
    description: Optional[str]
    value: Optional[Any]
    external_value: Optional[str]


class ParameterLocation(str, Enum):
    query = 'query'
    header = 'header'
    path = 'path'
    cookie = 'cookie'


class ParameterStyle(str, Enum):
    """
    See https://spec.openapis.org/oas/v3.1.0#style-values
    """
    matrix = 'matrix'
    label = 'label'
    form = 'form'
    simple = 'simple'
    space_delimited = 'spaceDelimited'
    pipe_delimited = 'pipeDelimited'
    deep_object = 'deepObject'


class Parameter(Model):
    """
    Describes a single operation parameter.

    A unique parameter is defined by a combination of a name and location.

    There are four possible parameter locations specified by the in field:

    - path - Used together with Path Templating, where the parameter value is actually part of the operation’s URL.
            This does not include the host or base path of the API. For example, in ```/items/{itemId}```,
            the path parameter is itemId.
    - query - Parameters that are appended to the URL. For example, in ```/items?id=###```, the query parameter is id.
    - header - Custom headers that are expected as part of the request.
               Note that [RFC7230] states header names are case insensitive.
    - cookie - Used to pass a specific cookie value to the API.
    """
    name: str
    location: ParameterLocation = Field(alias='in')
    description: Optional[str]
    required: Optional[bool]
    deprecated: Optional[bool]
    allow_empty_value: Optional[bool]
    style: Optional[ParameterStyle]
    explode: Optional[bool]
    allow_reserved: Optional[bool]
    schema_: Optional[Schema] = Field(alias='schema')
    example: Optional[Any]
    examples: Optional[Dict[str, Union[Reference, Example]]]
    content: Optional[Dict[str, 'MediaType']]


class Header(Parameter):
    """
    The Header Object follows the structure of the Parameter Object with the following changes:

    - name MUST NOT be specified, it is given in the corresponding headers map.
    - in MUST NOT be specified, it is implicitly in header.
    - All traits that are affected by the location MUST be applicable to a location of header (for example, style).
    """
    name: Optional[str]  # type: ignore
    location: Optional[ParameterLocation] = Field(alias='in')  # type: ignore


class Encoding(Model):
    """
    A single encoding definition applied to a single schema property.
    """
    content_type: Optional[str]
    headers: Optional[Dict[str, Union[Reference, Header]]]
    style: Optional[ParameterStyle]
    explode: Optional[bool]
    allow_reserved: Optional[bool]


class MediaType(Model):
    """
    Each Media Type Object provides schema and examples for the media type identified by its key.
    """
    schema_: Optional[Schema] = Field(alias='schema')
    example: Optional[Any]
    examples: Optional[Dict[str, Union[Reference, Example]]]
    encoding: Optional[Dict[str, Encoding]]


class RequestBody(Model):
    description: Optional[str]
    content: Dict[str, MediaType]
    required: Optional[bool]


class ServerVariable(Model):
    """
    An object representing a Server Variable for server URL template substitution.
    """
    enum: Optional[List[str]]
    default: str
    description: Optional[str]


class Server(Model):
    """
    An object representing a Server.
    """
    url: str
    description: Optional[str]
    variables: Optional[Dict[str, ServerVariable]]


class Link(Model):
    """
    The Link object represents a possible design-time link for a response.

    The presence of a link does not guarantee the caller’s ability to successfully invoke it,
    rather it provides a known relationship and traversal mechanism between responses and other operations.

    Unlike dynamic links (i.e. links provided in the response payload),
    the OAS linking mechanism does not require link information in the runtime response.

    For computing links, and providing instructions to execute them, a runtime expression
    is used for accessing values in an operation and using them as parameters while invoking the linked operation.
    """
    operation_ref: Optional[str]
    operation_id: Optional[str]
    parameters: Optional[Dict[str, Any]]
    request_body: Optional[Any]
    description: Optional[str]
    server: Optional[Server]


class Response(Model):
    """
    Describes a single response from an API Operation,
    including design-time, static links to operations based on the response.
    """
    description: str
    headers: Optional[Dict[str, Union[Reference, Header]]]
    content: Optional[Dict[str, MediaType]]
    links: Optional[Dict[str, Union[Reference, Link]]]


class SecuritySchemeType(str, Enum):
    api_key = 'apiKey'
    http = 'http'
    mutual_tls = 'mutualTLS'
    oauth2 = 'oauth2'
    open_id_connect = 'openIdConnect'


class SecuritySchemeLocation(str, Enum):
    query = 'query'
    header = 'header'
    cookie = 'cookie'


class OauthFlow(Model):
    """
    Configuration details for a supported OAuth Flow
    """
    authorization_url: Optional[str]
    token_url: Optional[str]
    refresh_url: Optional[str]
    scopes: Optional[Dict[str, str]]


class OauthFlows(Model):
    """
    Allows configuration of the supported OAuth Flows.
    """
    implicit: Optional[OauthFlow]
    password: Optional[OauthFlow]
    client_credentials: Optional[OauthFlow]
    authorization_code: Optional[OauthFlow]


class SecurityScheme(Model):
    """
    Defines a security scheme that can be used by the operations.

    Supported schemes are HTTP authentication, an API key (either as a header,
    a cookie parameter or as a query parameter), mutual TLS (use of a client certificate),
    OAuth2’s common flows (implicit, password, client credentials and authorization code)
    as defined in [RFC6749], and OpenID Connect Discovery.
    Please note that as of 2020, the implicit flow is about to be deprecated
    by OAuth 2.0 Security Best Current Practice. Recommended for most use case
    is Authorization Code Grant flow with PKCE.
    """
    type_: SecuritySchemeType = Field(alias='type')
    description: Optional[str]
    name: Optional[str]
    location: Optional[SecuritySchemeLocation] = Field(alias='in')
    scheme: Optional[str]
    bearer_format: Optional[str]
    flows: Optional[OauthFlows]
    open_id_connect_url: Optional[str]


Callback = Union['PathItem', Reference]
Callbacks = Dict[str, Callback]
"""
A map of possible out-of band callbacks related to the parent operation.

Each value in the map is a Path Item Object that describes a set of requests
that may be initiated by the API provider and the expected responses.
The key value used to identify the path item object is an expression,
evaluated at runtime, that identifies a URL to use for the callback operation.

To describe incoming requests from the API provider independent from another API call, use the webhooks field.
"""


class Components(Model):
    """
    Holds a set of reusable objects for different aspects of the OAS.

    All objects defined within the components object will
    have no effect on the API unless they are explicitly referenced
    from properties outside the components object.
    """
    schemas: Optional[Dict[str, Schema]]
    responses: Optional[Dict[str, Union[Reference, Response]]]
    parameters: Optional[Dict[str, Union[Reference, Parameter]]]
    examples: Optional[Dict[str, Union[Reference, Example]]]
    request_bodies: Optional[Dict[str, Union[Reference, RequestBody]]]
    headers: Optional[Dict[str, Union[Reference, Header]]]
    security_schemes: Optional[Dict[str, Union[Reference, SecurityScheme]]]
    links: Optional[Dict[str, Union[Reference, Link]]]
    callbacks: Optional[Dict[str, Union[Reference, Callbacks]]]
    path_items: Optional[Dict[str, Union[Reference, 'PathItem']]]


class Tag(Model):
    """
    Adds metadata to a single tag that is used by the Operation Object.

    It is not mandatory to have a Tag Object per tag defined in the Operation Object instances.
    """
    name: str
    description: Optional[str]
    external_docs: Optional[ExternalDocumentation]


class Contact(Model):
    """
    Contact information for the exposed API.
    """
    name: Optional[str]
    url: Optional[str]
    email: Optional[str]


class License(Model):
    """
    License information for the exposed API.
    """
    name: str
    identifier: Optional[str]
    url: Optional[str]


class Info(Model):
    """
    The object provides metadata about the API.

    The metadata MAY be used by the clients if needed,
    and MAY be presented in editing or documentation generation tools for convenience.
    """
    title: str
    summary: Optional[str]
    description: Optional[str]
    terms_of_service: Optional[str]
    contact: Optional[Contact]
    license: Optional[License]
    version: str


class SecurityRequirement(Dict[str, List[str]]):
    """
    Lists the required security schemes to execute this operation.

    The name used for each property MUST correspond to a security scheme
    declared in the Security Schemes under the Components Object.

    Security Requirement Objects that contain multiple schemes require that all schemes
    MUST be satisfied for a request to be authorized.
    This enables support for scenarios where multiple query parameters
    or HTTP headers are required to convey security information.

    When a list of Security Requirement Objects is defined on the OpenAPI Object or Operation Object,
    only one of the Security Requirement Objects in the list needs to be satisfied to authorize the request.

    Each name MUST correspond to a security scheme which
    is declared in the Security Schemes under the Components Object.
    If the security scheme is of type "oauth2" or "openIdConnect",
    then the value is a list of scope names required for the execution, and the list MAY be empty
    if authorization does not require a specified scope. For other security scheme types,
    the array MAY contain a list of role names which are required for the execution,
    but are not otherwise defined or exchanged in-band.
    """


class Operation(Model):
    """
    Describes a single API operation on a path.
    """
    tags: Optional[List[str]]
    summary: Optional[str]
    description: Optional[str]
    external_docs: Optional[ExternalDocumentation]
    operation_id: Optional[str]
    parameters: Optional[List[Union[Reference, Parameter]]]
    request_body: Optional[Union[Reference, RequestBody]]
    responses: Optional[Dict[str, Union[Reference, Response]]]
    callbacks: Optional[Dict[str, Union[Reference, Callbacks]]]
    deprecated: Optional[bool]
    security: Optional[List[SecurityRequirement]]
    servers: Optional[List[Server]]


class PathItem(Model):
    """
    Describes the operations available on a single path.

    A Path Item MAY be empty, due to ACL constraints.
    The path itself is still exposed to the documentation viewer but
    they will not know which operations and parameters are available.
    """
    ref: Optional[str] = Field(alias='$ref')
    summary: Optional[str]
    description: Optional[str]
    get: Optional[Operation]
    put: Optional[Operation]
    post: Optional[Operation]
    delete: Optional[Operation]
    options: Optional[Operation]
    head: Optional[Operation]
    patch: Optional[Operation]
    trace: Optional[Operation]
    servers: Optional[List[Server]]
    parameters: Optional[List[Union[Reference, Parameter]]]


class OpenAPI(Model):
    """
    This is the root object of the OpenAPI document.
    """
    openapi: str
    info: Info
    json_schema_dialect: Optional[str]
    servers: Optional[List[Server]]
    paths: Optional[Dict[str, PathItem]]
    webhooks: Optional[Dict[str, Union[Reference, PathItem]]]
    components: Optional[Components]
    security: Optional[List[SecurityRequirement]]
    tags: Optional[List[Tag]]
    external_docs: Optional[ExternalDocumentation]


Components.update_forward_refs()
Operation.update_forward_refs()
Parameter.update_forward_refs()
