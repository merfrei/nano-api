from flask import request
from flask_restful import Resource
from collections import namedtuple


ModelAPIFilter = namedtuple('ModelAPIFilter',
                            'column,value_type,filter_type,filter_expr')


class ModelListAPI(Resource):

    def __init__(self, *args, **kwargs):
        self.model_class = self.get_model_class()
        self.serializer = self.create_serializer()
        self.parser = self.create_parser()
        self._init_parser()
        self.db_session = self.get_db_session()
        super(ModelListAPI, self).__init__(*args, **kwargs)

    def _init_parser(self):
        self.serializer.parser_setup(self.parser)
        self.parser.add_argument('_limit', type=int)
        self.parser.add_argument('_offset', type=int)
        self.parser.add_argument('_sorted', type=str, action='append')
        self.parser.add_argument('_partial', type=bool, default=False)

    def create_serializer(self):
        raise NotImplementedError

    def create_parser(self):
        raise NotImplementedError

    def get_model_class(self):
        raise NotImplementedError

    def get_db_session(self):
        raise NotImplementedError

    def get_filters(self):
        # [(<col>, <col_type>, <filter_type>, <exp>), ...]
        # ie: [('name', str, 'ilike', '%%%s%%')]
        return []

    def get_order(self):
        # ie: [Model.name.desc(), Model.something.asc(), ...]
        return []

    def get(self):
        args = self.parser.parse_args()
        model_class = self.model_class
        query = model_class.query

        for col_name, col_type, filter_type, filter_exp in self.get_filters():
            filter_val = args.get(col_name)

            if filter_val:
                if col_type == bool:
                    filter_val = False if filter_val == '0' else True
                else:
                    filter_val = col_type(filter_val)
                if filter_type and filter_exp:
                    query = query.filter(
                        getattr(
                            getattr(model_class, col_name),
                            filter_type)(filter_exp % filter_val))
                else:
                    query = query.filter(
                        getattr(model_class, col_name) == filter_val)

        sorted_params = args.get('_sorted')
        if not sorted_params:
            order = self.get_order()
            if order:
                query = query.order_by(*order)
        else:
            order = []
            for s_param in sorted_params:
                # ie: 'attr,desc'
                spvls = s_param.split(',')
                if len(spvls) > 1:
                    # ie: ['attr', 'desc'] => Model.attr.desc()
                    order.append(getattr(getattr(model_class, spvls[0]), spvls[1])())
                else:
                    order.append(getattr(model_class, spvls[0]))
            if order:
                query = query.order_by(*order)

        offset = args.get('_offset')
        limit = args.get('_limit')
        if offset is not None:
            query = query.offset(int(offset))
        if limit is not None:
            query = query.limit(int(limit))

        all_list = []
        count = 0
        for model_obj in query:
            count += 1
            all_list.append(model_obj.serialize())

        return {'status': 'success',
                'data': all_list,
                'message': '%s records found' % count}, 200

    def post(self):
        args = self.parser.parse_args()
        model_class = self.model_class
        model_obj = model_class()
        self.serializer.populate(model_obj, args, request, self.db_session,
                                 partial=args['_partial'])
        self.db_session.add(model_obj)
        self.db_session.commit()

        return {'status': 'success',
                'data': model_obj.serialize(),
                'message': 'New item added'}, 201


class ModelAPI(Resource):

    def __init__(self, *args, **kwargs):
        self.model_class = self.get_model_class()
        self.serializer = self.create_serializer()
        self.parser = self.create_parser()
        self._init_parser()
        self.db_session = self.get_db_session()

        super(ModelAPI, self).__init__(*args, **kwargs)

    def _init_parser(self):
        self.serializer.parser_setup(self.parser)
        self.parser.add_argument('_partial', type=bool, default=True)

    def create_serializer(self):
        raise NotImplementedError

    def create_parser(self):
        raise NotImplementedError

    def get_model_class(self):
        raise NotImplementedError

    def get_db_session(self):
        raise NotImplementedError

    def get(self, ident):
        model_class = self.model_class
        model_obj = model_class.query.get(int(ident))
        if model_obj is None:
            return {'status': 'error',
                    'data': {},
                    'message': 'Item not found'}, 404

        return {'status': 'success',
                'data': model_obj.serialize(),
                'message': 'Item found'}, 200

    def put(self, ident):
        args = self.parser.parse_args()
        model_class = self.model_class
        model_obj = model_class.query.get(int(ident))
        if model_obj is None:
            return {'status': 'error',
                    'data': {},
                    'message': 'Item not found'}, 404
        self.serializer.populate(model_obj, args, request, self.db_session,
                                 partial=args['_partial'])
        self.db_session.add(model_obj)
        self.db_session.commit()

        return {'status': 'success',
                'data': model_obj.serialize(),
                'message': 'Item updated'}, 201

    def delete(self, ident):
        model_class = self.model_class
        model_obj = model_class.query.get(int(ident))
        if model_obj is None:
            return {'status': 'error',
                    'data': {},
                    'message': 'Item not found'}, 404
        model_class.query\
            .filter(model_class.id == model_obj.id)\
            .delete(synchronize_session=False)
        self.db_session.commit()

        return {'status': 'success',
                'data': {},
                'message': 'Item removed'}, 200


class ModelAPICreator(object):
    """Create a ModelAPI/ModelListAPI class dinamically"""
    def __init__(self, parser_class, db_session, *, decorators=None):
        self.parser_class = parser_class
        self.db_session = db_session
        self.decorators = decorators or ()

    def __call__(self, model_class, serializer_class):

        class NewModelAPI(ModelAPI):
            decorators = self.decorators

            def create_parser(self_):
                return self.parser_class()

            def get_db_session(self_):
                return self.db_session

            def create_serializer(self_):
                return serializer_class()

            def get_model_class(self_):
                return model_class

        class NewModelListAPI(ModelListAPI):
            decorators = self.decorators

            def create_parser(self_):
                return self.parser_class()

            def get_db_session(self_):
                return self.db_session

            def create_serializer(self_):
                return serializer_class()

            def get_model_class(self_):
                return model_class

        return NewModelAPI, NewModelListAPI
