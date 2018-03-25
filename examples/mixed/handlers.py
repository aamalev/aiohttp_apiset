
DB = {}


def set_document(request, doc_id, body, errors):
    """ Simple handler for set document
    ---
    tags: [documents]
    description: Set document
    parameters:
      - name: doc_id
        in: path
        type: integer
        minimum: 0
      - name: body
        in: body
        schema:
          $ref: swagger.yaml#/definitions/Document
    responses:
      200:
        description: OK
      400:
        description: Validation error
    """
    if doc_id in DB:
        errors['doc_id'].add('Document already exists')

    if errors:
        raise errors

    body['doc_id'] = doc_id
    DB[doc_id] = body

    # dict response for jsonify middleware
    return body
