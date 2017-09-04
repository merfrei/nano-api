Custom Flask API Utils
======================

Custom and simple API utils to be used in conjunction with Flask and Flask-Restful

## How to use example

models.py

```python
class Website(db.Model):
    __tablename__ = 'websites'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False, unique=True)
    url = db.Column(db.String(1024), nullable=False, unique=True)
    active = db.Column(db.Boolean, default=True)

    @db.validates('url')
    def validate_url(self, key, value):
        if not validators.url(value):
            raise ValueError('Wrong url for field: %s' % key)
        return value

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'active': self.active,
        }

    def __repr__(self):
        return '<Website %s>' % self.name


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer,
                           db.ForeignKey('websites.id', ondelete='cascade'),
                           nullable=False)
    website = db.relationship('Website',
                              backref=db.backref('tags', lazy='dynamic'))
    name = db.Column(db.String(256), nullable=False)

    def serialize(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'name': self.name,
        }

    def __repr__(self):
        return '<PageTag %s>' % self.id


website_page_tags = db.Table(
    'website_page_tags',
    db.Column('website_page_id', db.Integer,
              db.ForeignKey('website_pages.id',
                            ondelete='cascade')),
    db.Column('tag_id', db.Integer,
              db.ForeignKey('tags.id',
                            ondelete='cascade'))
)


class WebsitePage(db.Model):
    __tablename__ = 'website_pages'

    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer,
                           db.ForeignKey('websites.id', ondelete='cascade'),
                           nullable=False)
    website = db.relationship('Website',
                              backref=db.backref('pages', lazy='dynamic'))
    name = db.Column(db.String(256), nullable=False)
    example_url = db.Column(db.String(1024))
    tags = db.relationship('Tag',
                           secondary=website_page_tags,
                           backref=db.backref('website_pages',
                                              lazy='dynamic'))

    @db.validates('example_url')
    def validate_url(self, key, value):
        if not validators.url(value):
            raise ValueError('Wrong url for field: %s' % key)
        return value

    def serialize(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'name': self.name,
            'example_url': self.example_url,
            'tags': [t.id for t in self.tags],
        }

    def __repr__(self):
        return '<Page %s>' % self.id

```

serializers.py

```python
from api.models import Tag
from flask_serializer import Serializer
from flask_serializer import SerializerAttribute


class WebsiteSerializer(Serializer):
    def get_attributes(self):
        return [
            SerializerAttribute(name='name', type_=str, params=None),
            SerializerAttribute(name='url', type_=str, params=None),
            SerializerAttribute(name='active', type_=bool, params=None),
        ]


class TagSerializer(Serializer):
    def get_attributes(self):
        return [
            SerializerAttribute(name='website_id', type_=int, params=None),
            SerializerAttribute(name='name', type_=str, params=None),
        ]


class WebsitePageSerializer(Serializer):
    def get_attributes(self):
        return [
            SerializerAttribute(name='website_id', type_=int, params=None),
            SerializerAttribute(name='name', type_=str, params=None),
            SerializerAttribute(name='example_url', type_=str, params=None),
            SerializerAttribute(name='tags', type_=int,
                                params={'action': 'append'}),
        ]

    def get_relationships(self):
        return {
            'tags': {
                'model_class': Tag,
            },
        }

```

resources.py

```python
# ...
from api.models import Website
from api.serializers import WebsiteSerializer
from api.models import Tag
from api.serializers import TagSerializer
from api.models import WebsitePage
from api.serializers import WebsitePageSerializer
from flask_api import ModelAPICreator
from flask_api import ModelAPIFilter
# ...

mac = ModelAPICreator(RequestParser, db.session,
                      decorators=(auth.login_required,))

WebsiteAPI, WebsiteListAPI = mac(Website, WebsiteSerializer)
TagAPI, TagListAPI = mac(Tag, TagSerializer)
WebsitePageAPI, WebsitePageListAPI = mac(WebsitePage, WebsitePageSerializer)


class WebsiteListAPIExtended(WebsiteListAPI):
    """WebsiteListAPI with extra filters and order"""
    def get_filters(self):
        return [
            ModelAPIFilter(column='name', value_type=str,
                           filter_type='ilike', filter_expr='%%%s%%'),
        ]

    def get_order(self):
        return [Website.name.asc()]


class TagListAPIExtended(TagListAPI):
    """TagListAPI with extra filters and order"""
    def get_filters(self):
        return [
            ModelAPIFilter(column='website_id', value_type=int,
                           filter_type=None, filter_expr=None),
        ]

    def get_order(self):
        return [Tag.name.asc()]


class WebsitePageListAPIExtended(WebsitePageListAPI):
    """WebsitePageListAPI with extra filters and order"""
    def get_filters(self):
        return [
            ModelAPIFilter(column='website_id', value_type=int,
                           filter_type=None, filter_expr=None),
        ]

    def get_order(self):
        return [WebsitePage.name.asc()]
```
