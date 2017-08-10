from collections import namedtuple


def check_is_iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    return True


class SerializerError(Exception):
    pass


SerializerAttribute = namedtuple('SerializerAttribute', 'name, type_, params')


class Serializer(object):

    def __init__(self):
        attrs = self.get_attributes()
        self._validate_attributes(attrs)

        self._attrs = attrs
        self._relationships = self.get_relationships()

    def get_attributes(self):
        raise NotImplementedError

    def get_relationships(self):
        return {}

    @staticmethod
    def _check_valid_attr(attr):
        valid_len = len(attr) == 3
        valid_type = (isinstance(attr[0], str) and
                      isinstance(attr[1], type) and
                      (attr[2] is None or isinstance(attr[2], dict)))
        return (valid_len and valid_type)

    @classmethod
    def _validate_attributes(cls, attrs):
        is_iterable = check_is_iterable(attrs)
        if not is_iterable:
            raise SerializerError('Attributes object must be iterable in %r' % cls)
        elif not all([cls._check_valid_attr(attr) for attr in attrs]):
            raise SerializerError('Wrong format for attributes in %r' % cls)

    def parser_setup(self, parser):
        for attr_name, attr_type, params in self._attrs:
            if params is not None:
                parser.add_argument(attr_name, attr_type, **params)
            else:
                parser.add_argument(attr_name, attr_type)

    def populate(self, model_obj, args, request, db_session, *, partial=False):
        attrs_dict = {a[0]: a[1] for a in self._attrs}
        for k, v in args.items():
            if k in attrs_dict:
                request_params = set(request.values.keys())
                if request.json:
                    request_params = request_params.union(
                        set(request.json.keys()))
                if k not in request_params and partial:
                    continue
                if k in self._relationships:
                    setattr(model_obj, k, [])
                    if v is None or v == 0:
                        # empty list
                        continue
                    relation_details = self._relationships[k]
                    rel_model_class = relation_details['model_class']
                    rel_model_query = getattr(rel_model_class, 'query')
                    if 'split' in relation_details:
                        v = [s.strip() for s in v.split(',')]

                    for obj_val in v:
                        model_field = relation_details.get('model_field')
                        if model_field:
                            obj_fld = getattr(rel_model_class, model_field)
                            rel_model_obj = rel_model_query\
                                .filter(obj_fld == obj_val)\
                                .first()
                        else:
                            # Get by id
                            rel_model_obj = rel_model_query.get(int(obj_val))

                        # Record does not exist?
                        # Should it create a new one?
                        not_exists = rel_model_obj is None
                        force_create = relation_details.get('force_create', False)
                        if not_exists and force_create and model_field:
                            rel_model_obj = rel_model_class()
                            setattr(rel_model_obj, model_field, obj_val)
                            db_session.add(rel_model_obj)
                            db_session.commit()
                        if model_obj:
                            getattr(model_obj, k).append(rel_model_obj)
                elif k in self._relationships and not v:
                    continue
                else:
                    try:
                        setattr(model_obj, k, attrs_dict[k](v))
                    except:
                        setattr(model_obj, k, None)
