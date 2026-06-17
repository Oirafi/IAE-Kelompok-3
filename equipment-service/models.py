from bson import ObjectId


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict by converting ObjectId to str."""
    if doc is None:
        return None
    doc['_id'] = str(doc['_id'])
    return doc


def to_object_id(id_str):
    """Safely convert a string to ObjectId. Returns None if invalid."""
    try:
        return ObjectId(id_str)
    except Exception:
        return None
